"""Batched ``_process_market`` (source lines 519-694).

The order **index** is a priority lane: the interpreter walks index 0 for both
players, drains the price curve, then moves to index 1.  That is preserved here
as an explicit Python loop over the <=10 order slots -- 10 vectorised passes,
never a loop over envs.

Within one index the source runs a "per-unit lockstep": both players are quoted
against the same pre-commit inventory, then both commit (player order).  A
player's commit only touches its own money/shed/seeds plus an *additive* delta on
the shared market inventory, so within one lockstep round the two commits are
order-independent and can be applied together.

Two implementations of that lockstep live here:

``_lane_loop``   the literal transcription -- one vectorised pass per unit.
                 Always correct, but its length is the max units traded across
                 the batch.
``_lane_fast``   closed forms for every case where the two players' orders do not
                 touch the same market item, plus an exact closed form for the
                 mirror case (both SELL the same item, which is what self-play
                 does at index 0).  Uses prefix sums of the price table, so a
                 120-unit melon dump costs O(1) instead of 120 passes.  Anything
                 left over (SELL vs BUY_PRODUCT on the same item, etc.) falls
                 back to ``_lane_loop`` for the affected envs only.

``_lane_fast`` is the default; ``VecKaggriculture(market_exact_loop=True)``
switches to the loop, and ``tests/test_market_equiv.py`` checks they agree.
"""

from __future__ import annotations

import torch

from . import ops as O
from ._consts import FARM_HAND_COST_MULT, MAX_MARKET_ORDERS
from ._tables import get_tables

MARKET_UNIT_CAP = 100_000
_BSEARCH_ITERS = 20


# --------------------------------------------------------------------------- #
def _do_hire(st, mask, tab, max_hands: int, mult: int = FARM_HAND_COST_MULT):
    """Source 670-677 (+ _spawn_hand 508-516)."""
    cost = tab.fib[st.hires_today.to(torch.int64).clamp(0, tab.fib.shape[0] - 1)] * mult
    ok = mask & (st.money >= cost)
    st.money -= torch.where(ok, cost, 0)
    st.hires_today += ok.to(st.hires_today.dtype)

    u_range = torch.arange(st.ux.shape[2], device=st.ux.device)
    live = u_range.view(1, 1, -1) <= st.n_hands.unsqueeze(-1)
    pos = st.uy.to(torch.int64) * 10 + st.ux.to(torch.int64)
    occ = ((pos.unsqueeze(-1) == tab.shed_access_flat.view(1, 1, 1, -1))
           & live.unsqueeze(-1)).sum(2)                       # [B, 2, 4]
    key = occ * 8 + torch.arange(4, device=occ.device).view(1, 1, -1)
    tile = tab.shed_access_flat[key.argmin(dim=-1)]
    nx = (tile % 10).to(st.ux.dtype)
    ny = (tile // 10).to(st.uy.dtype)

    stored = ok & (st.n_hands < max_hands)
    slot = (st.n_hands.to(torch.int64) + 1).clamp(0, st.ux.shape[2] - 1).unsqueeze(-1)
    st.ux.scatter_(-1, slot, torch.where(stored, nx, st.ux.gather(-1, slot).squeeze(-1)).unsqueeze(-1))
    st.uy.scatter_(-1, slot, torch.where(stored, ny, st.uy.gather(-1, slot).squeeze(-1)).unsqueeze(-1))
    st.n_hands += stored.to(st.n_hands.dtype)
    st.overflow += (ok & ~stored).to(st.overflow.dtype)


def _do_buy_land(st, mask, tab):
    """Source 680-693."""
    li = st.land.to(torch.int64).clamp(0, 2)
    cost = tab.land_prices[li]
    ok = mask & (st.land < 3) & (st.money >= cost)
    st.money -= torch.where(ok, cost, 0)
    qmask = tab.quadrant_mask[tab.land_quadrant[li]]          # [B, 2, 100]
    unlock = ok.unsqueeze(-1) & qmask & (st.kind == O.TILE_LOCKED)
    st.kind.copy_(torch.where(unlock, O.TILE_EMPTY, st.kind))
    st.land += ok.to(st.land.dtype)


# --------------------------------------------------------------------------- #
def _classify(op, item, qty):
    is_sell = (op == O.MKT_SELL) & (item >= 0) & (item < O.N_PRODUCTS)
    is_bp = (op == O.MKT_BUY_PRODUCT) & ((item == O.ITEM_WHEAT) | (item == O.ITEM_FERTILIZER))
    is_bs = (op == O.MKT_BUY_SEED) & (item >= 0) & (item < O.N_CROPS)
    is_ba = (op == O.MKT_BUY_ANIMAL) & (item >= O.ITEM_GOOSE) & (item < O.ITEM_GOOSE + O.N_ANIMALS)
    active = (is_sell | is_bp | is_bs | is_ba) & (qty > 0)
    return is_sell, is_bp, is_bs, is_ba, active


def _quote(st, tab, is_sell, is_bp, is_bs, is_ba, item):
    inv_here = st.market_inv.gather(-1, item.clamp(0, O.N_PRODUCTS - 1))
    ip = item.clamp(0, O.N_PRODUCTS - 1)
    p_sell = tab.price[ip, (inv_here - tab.inv_lo).clamp(0, tab.inv_n - 1)]
    p_buy = tab.price[ip, (inv_here - 1 - tab.inv_lo).clamp(0, tab.inv_n - 1)]
    price = torch.where(is_sell, p_sell, torch.zeros_like(p_sell))
    price = torch.where(is_bp, p_buy, price)
    price = torch.where(is_bs, tab.crop_seed_cost[item.clamp(0, O.N_CROPS - 1)], price)
    price = torch.where(is_ba, tab.animal_cost[(item - O.ITEM_GOOSE).clamp(0, O.N_ANIMALS - 1)],
                        price)
    return price


# --------------------------------------------------------------------------- #
def _lane_loop(st, tab, op, item, qty, active_in=None, stats=None):
    """Literal per-unit lockstep (source 557-601)."""
    is_sell, is_bp, is_bs, is_ba, active = _classify(op, item, qty)
    if active_in is not None:
        active = active & active_in
    remaining = torch.where(active, qty, 0)

    price0 = _quote(st, tab, is_sell, is_bp, is_bs, is_ba, item)
    item_i = item.clamp(0, O.N_ITEMS - 1)
    shed_here = st.shed.gather(-1, item_i.unsqueeze(-1)).squeeze(-1)
    bound = torch.where(is_sell, torch.minimum(remaining, shed_here), torch.zeros_like(remaining))
    bound = torch.where(is_bp | is_bs | is_ba,
                        torch.minimum(remaining, st.money // price0.clamp(min=1)), bound)
    bound = torch.where(active, bound, torch.zeros_like(bound))
    n_rounds = int(bound.max().item())
    if n_rounds <= 0:
        return
    n_rounds = min(n_rounds, MARKET_UNIT_CAP)
    if stats is not None:
        stats["market_rounds"] = stats.get("market_rounds", 0) + n_rounds

    item_p = item.clamp(0, O.N_PRODUCTS - 1)
    crop_i = item.clamp(0, O.N_CROPS - 1).unsqueeze(-1)
    item_iu = item_i.unsqueeze(-1)
    for _ in range(n_rounds):
        alive = active & (remaining > 0)
        price = _quote(st, tab, is_sell, is_bp, is_bs, is_ba, item)
        shed_here = st.shed.gather(-1, item_iu).squeeze(-1)
        ok_sell = alive & is_sell & (shed_here > 0)
        ok_buy = alive & (is_bp | is_bs | is_ba) & (st.money >= price)
        ok = ok_sell | ok_buy

        st.money += torch.where(ok_sell, price, 0) - torch.where(ok_buy, price, 0)
        d_shed = (ok & (is_bp | is_ba)).to(torch.int64) - ok_sell.to(torch.int64)
        st.shed.scatter_add_(-1, item_iu, d_shed.unsqueeze(-1))
        st.seeds.scatter_add_(-1, crop_i, (ok & is_bs).to(torch.int64).unsqueeze(-1))
        d_mkt = (ok_sell & (price > 1)).to(torch.int64) - (ok & is_bp).to(torch.int64)
        st.market_inv.scatter_add_(-1, item_p, d_mkt)

        remaining = remaining - ok.to(remaining.dtype)
        active = active & (~alive | ok)


# --------------------------------------------------------------------------- #
def _sell_closed(tab, item, v0, cmax):
    """One player selling ``cmax`` units alone from table coord ``v0``.

    Returns (revenue, market-inventory delta).  Once the price reaches the floor
    the source stops crediting supply (``if price > 1``), so inventory advances
    by at most ``floor_idx - v0`` and the rest sells at $1.
    """
    n = tab.inv_n
    floor = tab.price_floor_idx[item]
    k = torch.minimum(cmax, (floor - v0).clamp(min=0))
    cum = tab.price_cumsum
    rev = (cum[item, (v0 + k).clamp(0, n)] - cum[item, v0.clamp(0, n)]) + (cmax - k)
    return rev, k


def _bp_closed(tab, item, v0, money, n):
    """BUY_PRODUCT: prices are P(v0-1), P(v0-2), ... (rising).  The largest k with
    cumulative cost <= money, found by binary search on the price prefix sums."""
    cum = tab.price_cumsum
    base = cum[item, v0.clamp(0, tab.inv_n)]
    target = base - money
    lo = (v0 - n).clamp(min=0)
    hi = v0.clone()
    for _ in range(_BSEARCH_ITERS):
        mid = (lo + hi) // 2
        ge = cum[item, mid.clamp(0, tab.inv_n)] >= target
        hi = torch.where(ge, mid, hi)
        lo = torch.where(ge, lo, mid + 1)
    k = (v0 - lo).clamp(min=0).minimum(n)
    cost = base - cum[item, (v0 - k).clamp(0, tab.inv_n)]
    return k, cost


def _lane_fast(st, tab, op, item, qty, need_bp: bool, coupled_any: bool, stats=None):
    is_sell, is_bp, is_bs, is_ba, active = _classify(op, item, qty)

    is_mkt = is_sell | is_bp
    both = active[:, 0] & active[:, 1]
    same = both & is_mkt[:, 0] & is_mkt[:, 1] & (item[:, 0] == item[:, 1])
    both_sell = same & is_sell[:, 0] & is_sell[:, 1]
    coupled = same & ~both_sell

    if coupled_any:
        _lane_loop(st, tab, op, item, qty, active_in=coupled.unsqueeze(-1), stats=stats)
    fast = active & ~coupled.unsqueeze(-1)

    item_i = item.clamp(0, O.N_ITEMS - 1)
    item_p = item.clamp(0, O.N_PRODUCTS - 1)
    crop_i = item.clamp(0, O.N_CROPS - 1)
    v0 = st.market_inv.gather(-1, item_p) - tab.inv_lo

    # ---- fixed-price orders (BUY_SEED / BUY_ANIMAL) -------------------------
    m_fixed = fast & (is_bs | is_ba)
    cost1 = torch.where(is_bs, tab.crop_seed_cost[crop_i],
                        tab.animal_cost[(item - O.ITEM_GOOSE).clamp(0, O.N_ANIMALS - 1)])
    cnt = torch.where(m_fixed, torch.minimum(qty, st.money // cost1.clamp(min=1)), 0)
    st.money -= cnt * cost1
    st.seeds.scatter_add_(-1, crop_i.unsqueeze(-1),
                          torch.where(is_bs, cnt, 0).unsqueeze(-1))
    st.shed.scatter_add_(-1, item_i.unsqueeze(-1),
                         torch.where(is_ba, cnt, 0).unsqueeze(-1))

    # ---- BUY_PRODUCT (never same-item across players here) ------------------
    if need_bp:
        m_bp = fast & is_bp
        kbp, cost = _bp_closed(tab, item_p, v0, st.money, qty)
        kbp = torch.where(m_bp, kbp, 0)
        cost = torch.where(m_bp, cost, 0)
        st.money -= cost
        st.shed.scatter_add_(-1, item_i.unsqueeze(-1), kbp.unsqueeze(-1))
        st.market_inv.scatter_add_(-1, item_p, -kbp)
        v0 = v0 - kbp                      # keep the local copy in sync

    # ---- SELL ---------------------------------------------------------------
    m_sell = fast & is_sell
    shed_here = st.shed.gather(-1, item_i.unsqueeze(-1)).squeeze(-1)
    cmax = torch.where(m_sell, torch.minimum(qty, shed_here), 0)

    solo = m_sell & ~both_sell.unsqueeze(-1)
    rev, dinv = _sell_closed(tab, item_p, v0, cmax)
    rev = torch.where(solo, rev, 0)
    dinv = torch.where(solo, dinv, 0)

    if True:                                # mirror (both players, same item)
        i0 = item_p[:, 0]
        w0 = v0[:, 0]
        c0, c1 = cmax[:, 0], cmax[:, 1]
        kmin = torch.minimum(c0, c1)
        d = (tab.price_floor_idx[i0] - w0).clamp(min=0)
        kk = torch.minimum(kmin, (d + 1) // 2)
        suf = tab.price_suf2
        rev_each = (suf[i0, w0.clamp(0, tab.inv_n)] - suf[i0, (w0 + 2 * kk).clamp(0, tab.inv_n)]
                    + (kmin - kk))
        rev_x, dinv_x = _sell_closed(tab, i0, w0 + 2 * kk, torch.maximum(c0, c1) - kmin)
        rev_each = torch.where(both_sell, rev_each, 0)
        rev_x = torch.where(both_sell, rev_x, 0)
        dinv_j = torch.where(both_sell, 2 * kk + dinv_x, 0)
        rev = rev + torch.stack([rev_each + torch.where(c0 > c1, rev_x, 0),
                                 rev_each + torch.where(c1 > c0, rev_x, 0)], dim=1)
        st.market_inv.scatter_add_(-1, i0.unsqueeze(-1), dinv_j.unsqueeze(-1))

    st.money += rev
    st.shed.scatter_add_(-1, item_i.unsqueeze(-1), -cmax.unsqueeze(-1))
    st.market_inv.scatter_add_(-1, item_p, dinv)


# --------------------------------------------------------------------------- #
N_SLOT_FLAGS = 5


def slot_flags(market_actions) -> torch.Tensor:
    """``[n_slots, 5]`` bool: (any order, any HIRE, any BUY_LAND, any BUY_PRODUCT,
    any same-item SELL/BUY_PRODUCT collision) -- which passes each order slot
    needs.  Derived from the actions alone, so the caller can fetch it to the
    host in the same transfer as everything else it needs this step.
    """
    n_slots = min(market_actions.shape[2], MAX_MARKET_ORDERS)
    ops_all = market_actions[:, :, :n_slots, 0]
    items_all = market_actions[:, :, :n_slots, 1]
    qty_all = market_actions[:, :, :n_slots, 2]
    is_sell, is_bp, is_bs, is_ba, active = _classify(ops_all, items_all, qty_all)
    is_mkt = is_sell | is_bp
    same = (active[:, 0] & active[:, 1] & is_mkt[:, 0] & is_mkt[:, 1]
            & (items_all[:, 0] == items_all[:, 1]))
    coupled = same & ~(is_sell[:, 0] & is_sell[:, 1])
    return torch.stack([
        (ops_all != O.MKT_NONE).any(1).any(0),
        (ops_all == O.MKT_HIRE).any(1).any(0),
        (ops_all == O.MKT_BUY_LAND).any(1).any(0),
        is_bp.any(1).any(0),
        coupled.any(0),
    ]).t()


def process_market(st, market_actions, max_hands: int, stats=None, exact_loop=False,
                   flags=None, graph_slot=None):
    """``market_actions``: int64 ``[B, 2, MAX_ORDERS, 3]``.

    ``flags``: optional host-side list of lists from ``slot_flags`` (pass it in to
    avoid a second device->host sync per step).
    ``graph_slot``: optional callable taking the slot's ``[B, 2, 3]`` action
    tensor; when supplied it handles every slot that needs no host-side
    branching (see ``market_slot_static``)."""
    tab = get_tables(str(st.money.device))
    n_slots = min(market_actions.shape[2], MAX_MARKET_ORDERS)
    ops_all = market_actions[:, :, :n_slots, 0]
    items_all = market_actions[:, :, :n_slots, 1]
    qty_all = market_actions[:, :, :n_slots, 2]
    if flags is None:
        flags = slot_flags(market_actions).tolist()

    for i in range(n_slots):
        used, has_hire, has_land, has_bp, has_coupled = flags[i]
        if not used:
            continue
        if (graph_slot is not None and not exact_loop
                and not has_bp and not has_coupled):
            # Cheap common case: no BUY_PRODUCT (no binary search) and no
            # same-item SELL/BUY_PRODUCT collision (no lockstep fallback), so the
            # slot is a fixed sequence of kernels -> replay it from a CUDA graph.
            graph_slot(market_actions[:, :, i, :])
            continue
        op = ops_all[:, :, i]
        if has_hire:
            _do_hire(st, op == O.MKT_HIRE, tab, max_hands)
        if has_land:
            _do_buy_land(st, op == O.MKT_BUY_LAND, tab)
        item = items_all[:, :, i]
        qty = qty_all[:, :, i]
        if exact_loop:
            _lane_loop(st, tab, op, item, qty, stats=stats)
        else:
            _lane_fast(st, tab, op, item, qty, bool(has_bp), bool(has_coupled), stats)


def market_slot_static(st, slot, max_hands: int):
    """One order slot with no host-side branching: HIRE, BUY_LAND and the
    closed-form lane, all mask-gated.  Assumes the slot needs neither the
    BUY_PRODUCT binary search nor the coupled-lane fallback (the caller checks
    that with the one sync it already does).  This is the CUDA-graph body."""
    tab = get_tables(str(st.money.device))
    op, item, qty = slot[:, :, 0], slot[:, :, 1], slot[:, :, 2]
    _do_hire(st, op == O.MKT_HIRE, tab, max_hands)
    _do_buy_land(st, op == O.MKT_BUY_LAND, tab)
    _lane_fast(st, tab, op, item, qty, False, False, None)
