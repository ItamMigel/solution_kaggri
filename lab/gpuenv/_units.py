"""Batched ``_apply_unit_action`` (source lines 297-505) plus the atomic PLANT
validation from ``interpreter`` (lines 888-901).

Units are applied strictly in source order -- farmer (index 0) then hands 0..n --
because later units observe earlier units' effects.  That is a Python loop over
``1 + MAX_HANDS`` iterations; every iteration is fully batched over ``[B, 2]``
(both envs and both players, which never interact here).

Everything here is written to be **CUDA-graph capturable**: state is mutated in
place, ``day``/``step`` arrive as 0-dim device tensors, and there is no
data-dependent Python control flow.
"""

from __future__ import annotations

import torch

from . import ops as O
from ._consts import BOARD_SIZE, HALF, SHED_CAPACITY, TURNS_PER_DAY
from ._tables import get_tables

_ORDER_SENTINEL = 1 << 40


# --------------------------------------------------------------------------- #
# small inventory helpers -- ``inv`` / ``order`` are [B, 2, 12] slices
# --------------------------------------------------------------------------- #
def _inv_add(inv, order, idx, n, mask, tick):
    delta = torch.where(mask, n, 0).unsqueeze(-1)
    cur = inv.gather(-1, idx)
    was_zero = (cur == 0) & (delta > 0)
    inv.scatter_add_(-1, idx, delta)
    order.scatter_(-1, idx, torch.where(was_zero, tick, order.gather(-1, idx)))


def _inv_take(inv, order, idx, n, mask):
    """Unconditional subtraction (callers must have checked availability)."""
    delta = torch.where(mask, n, 0).unsqueeze(-1)
    inv.scatter_add_(-1, idx, -delta)
    cur = inv.gather(-1, idx)
    order.scatter_(-1, idx, torch.where(cur == 0, _ORDER_SENTINEL, order.gather(-1, idx)))


def greedy_drop(shed, inv, order, room, mask):
    """Drop a unit's whole inventory into the shed in dict-insertion order.

    Mirrors the source's ``room = max(0, capacity - sum(shed))`` recomputed per
    item: the greedy prefix ``take_i = clip(room - sum_of_earlier_items, 0, n_i)``.

    Done without sorting.  There are only 12 item slots, so the exclusive prefix
    sum "over items inserted earlier than i" is one 12x12 masked reduction --
    which replaces an argsort + cumsum that together cost ~22% of the whole unit
    phase, on every unit of every step, for an op that almost never fires.
    Insertion ticks are unique within a unit (a unit performs at most one
    inventory-adding op per step), and slots that tie on the sentinel hold n = 0,
    so they neither contribute to nor receive anything -- exactly what the
    source's stable ordering does.
    """
    earlier = order.unsqueeze(-1) > order.unsqueeze(-2)        # [..., i, j]
    cum_excl = (inv.unsqueeze(-2) * earlier).sum(-1)
    take = (room.unsqueeze(-1) - cum_excl).clamp(min=0).minimum(inv)
    take = torch.where(mask.unsqueeze(-1), take, 0)
    shed.add_(take)                    # inv is already indexed by item id
    keep = ~mask.unsqueeze(-1)
    inv.mul_(keep)
    order.copy_(torch.where(keep, order, _ORDER_SENTINEL))


# --------------------------------------------------------------------------- #
def plant_blocked(unit_actions: torch.Tensor, seeds: torch.Tensor,
                  out: torch.Tensor | None = None) -> torch.Tensor:
    """[B, 2, 5] bool.  Source: total PLANT requests for a crop this turn beyond
    the available seeds cancels *all* of that crop's PLANT requests.

    Counts every action slot (the source counts ``[farmer, *hands_actions]``
    without checking the hand exists), so unused slots must carry OP_PASS.
    """
    op = unit_actions[..., 0]
    crop = unit_actions[..., 1]
    is_plant = (op == O.OP_PLANT) & (crop >= 0) & (crop < O.N_CROPS)
    idx = crop.clamp(0, O.N_CROPS - 1)
    demand = torch.zeros(seeds.shape, dtype=torch.int64, device=seeds.device)
    demand.scatter_add_(-1, idx, is_plant.to(torch.int64))
    res = demand > seeds
    if out is not None:
        out.copy_(res)
        return out
    return res


def apply_unit_actions(st, unit_actions, blocked, day, step, u_max: int):
    for u in range(u_max + 1):
        apply_one_unit(st, unit_actions, blocked, day, step, u)


def apply_one_unit(st, unit_actions, blocked, day, step, u: int):
    """``day`` / ``step`` may be Python ints or 0-dim device tensors."""
    tab = get_tables(str(st.money.device))
    op = unit_actions[:, :, u, 0]
    a1 = unit_actions[:, :, u, 1]
    a2 = unit_actions[:, :, u, 2]

    if u > 0:
        exists = st.n_hands >= u
        act = exists & (op != O.OP_PASS) & (op > 0) & (op < O.N_UNIT_OPS)
    else:
        act = (op > 0) & (op < O.N_UNIT_OPS)

    fx = st.ux[:, :, u].to(torch.int64)
    fy = st.uy[:, :, u].to(torch.int64)

    # ---------------- moves (source 308-316) ---------------------------------
    is_move = act & (op <= O.OP_WEST)
    mi = (op - O.OP_NORTH).clamp(0, 3)
    nx = fx + tab.move_dx[mi]
    ny = fy + tab.move_dy[mi]
    inb = (nx >= 0) & (nx < BOARD_SIZE) & (ny >= 0) & (ny < BOARD_SIZE)
    nflat = (ny.clamp(0, BOARD_SIZE - 1) * BOARD_SIZE + nx.clamp(0, BOARD_SIZE - 1)).unsqueeze(-1)
    # 1.32.7 permits crossing into a LOCKED tile.  This matters at the shed:
    # hands can spawn on one of its initially locked access tiles and otherwise
    # would be stranded.  Tile operations still retain the guard below.
    can_move = is_move & inb
    st.ux[:, :, u] = torch.where(can_move, nx, fx).to(st.ux.dtype)
    st.uy[:, :, u] = torch.where(can_move, ny, fy).to(st.uy.dtype)

    flat = (fy * BOARD_SIZE + fx).unsqueeze(-1)

    # ---------------- gather the standing tile -------------------------------
    k = st.kind.gather(-1, flat).squeeze(-1).to(torch.int64)
    sp = st.species.gather(-1, flat).squeeze(-1).to(torch.int64)
    td = st.tday.gather(-1, flat).squeeze(-1).to(torch.int64)
    ty = st.tyield.gather(-1, flat).squeeze(-1).to(torch.int64)
    tw = st.tflag.gather(-1, flat).squeeze(-1)
    tc = st.tcons.gather(-1, flat).squeeze(-1).to(torch.int64)
    tm = st.tmls.gather(-1, flat).squeeze(-1).to(torch.int64)
    tf = st.tfert.gather(-1, flat).squeeze(-1).to(torch.int64)
    tcr = st.tcared.gather(-1, flat).squeeze(-1)
    tfa = st.tfavail.gather(-1, flat).squeeze(-1)
    tcb = st.tcare.gather(-1, flat).squeeze(-1).to(torch.int64)

    # The 1.32.7 interpreter resolves PICKUP/DROP before rejecting operations
    # on a LOCKED tile: three shed-access tiles begin locked, yet must remain
    # usable as standing positions.  Other tile operations still no-op there.
    shed_op = ((op == O.OP_PICKUP) | (op == O.OP_DROP) | (op == O.OP_PLACE))
    act = act & ~is_move & ((k != O.TILE_LOCKED) | shed_op)

    is_plant = k == O.TILE_PLANT
    is_animal = k == O.TILE_ANIMAL
    is_empty = k == O.TILE_EMPTY

    inv = st.inv[:, :, u, :]
    order = st.inv_order[:, :, u, :]
    shed = st.shed

    item_ok = (a1 >= 0) & (a1 < O.N_ITEMS)
    item_i = a1.clamp(0, O.N_ITEMS - 1).unsqueeze(-1)
    crop = a1.clamp(0, O.N_CROPS - 1)
    crop_i = crop.unsqueeze(-1)
    fert_i = torch.full_like(item_i, O.ITEM_FERTILIZER)
    wheat_i = torch.zeros_like(item_i)          # ITEM_WHEAT == 0
    one = torch.ones_like(td)

    shed_adj = ((fx == HALF - 1) | (fx == HALF)) & ((fy == HALF - 1) | (fy == HALF))
    room = (SHED_CAPACITY - shed.sum(-1)).clamp(min=0)

    new_k, new_sp, new_td, new_ty = k, sp, td, ty
    new_tw, new_tc, new_tm, new_tf = tw, tc, tm, tf
    new_tcr, new_tfa, new_tcb = tcr, tfa, tcb

    # ---------------- DROP (325-338) -----------------------------------------
    greedy_drop(shed, inv, order, room, act & (op == O.OP_DROP) & shed_adj)

    # ---------------- PICKUP (340-357) ---------------------------------------
    m_pick = act & (op == O.OP_PICKUP) & shed_adj & (a2 > 0) & item_ok
    npick = torch.minimum(a2, shed.gather(-1, item_i).squeeze(-1))
    m_pick = m_pick & (npick > 0)
    shed.scatter_add_(-1, item_i, -torch.where(m_pick, npick, 0).unsqueeze(-1))
    _inv_add(inv, order, item_i, npick, m_pick, step)

    # ---------------- PLANT (359-371) ----------------------------------------
    m_plant = (act & (op == O.OP_PLANT) & (a1 >= 0) & (a1 < O.N_CROPS)
               & is_empty & (st.seeds.gather(-1, crop_i).squeeze(-1) > 0)
               & ~blocked.gather(-1, crop_i).squeeze(-1))
    st.seeds.scatter_add_(-1, crop_i, -m_plant.to(torch.int64).unsqueeze(-1))
    ongoing = tab.crop_ongoing[crop]
    new_k = torch.where(m_plant, O.TILE_PLANT, new_k)
    new_sp = torch.where(m_plant, crop, new_sp)
    new_td = torch.where(m_plant, day, new_td)
    new_ty = torch.where(m_plant, (~ongoing).to(torch.int64), new_ty)
    new_tw = new_tw & ~m_plant
    new_tc = torch.where(m_plant, one, new_tc)
    new_tm = torch.where(m_plant,
                         torch.where(ongoing, -one,
                                     (day + tab.crop_max_yield_day[crop] + 1) * TURNS_PER_DAY),
                         new_tm)
    new_tf = torch.where(m_plant, -one, new_tf)
    new_tcr = new_tcr & ~m_plant
    new_tfa = new_tfa & ~m_plant
    new_tcb = torch.where(m_plant, 0, new_tcb)

    # ---------------- WATER (373-386) ----------------------------------------
    m_water = act & (op == O.OP_WATER) & is_plant & ~tw
    spc = sp.clamp(0, O.N_CROPS - 1)
    age = day - td
    in_window = ((~tab.crop_ongoing[spc]) & (age >= tab.crop_window_start[spc])
                 & (age <= tab.crop_max_yield_day[spc]))
    bonus = 1 + (tf >= day).to(torch.int64)
    new_ty = torch.where(m_water & in_window,
                         torch.minimum(tab.crop_max_yield[spc], ty + bonus), new_ty)
    new_tw = new_tw | m_water

    # ---------------- HARVEST (388-415) --------------------------------------
    m_h = act & (op == O.OP_HARVEST) & (is_plant | is_animal) & (ty > 0)
    c_ongoing = tab.crop_ongoing[spc]
    m_hp = m_h & is_plant & (age >= tab.crop_first_yield[spc])
    m_ha = m_h & is_animal
    prod = torch.where(is_plant, spc, tab.animal_product[sp.clamp(0, O.N_ANIMALS - 1)])
    m_harv = m_hp | m_ha
    _inv_add(inv, order, prod.unsqueeze(-1), ty, m_harv, step)
    new_ty = torch.where(m_harv, 0, new_ty)
    new_k = torch.where(m_hp & ~c_ongoing, O.TILE_EMPTY, new_k)

    # ---------------- FERTILIZE (417-424) ------------------------------------
    m_fert = (act & (op == O.OP_FERTILIZE) & is_plant
              & (inv.gather(-1, fert_i).squeeze(-1) > 0))
    _inv_take(inv, order, fert_i, one, m_fert)
    new_tf = torch.where(m_fert, torch.maximum(tf, (day + 2) * one), new_tf)

    # ---------------- DIG (426-433) ------------------------------------------
    new_k = torch.where(act & (op == O.OP_DIG) & ~is_empty & ~is_animal,
                        O.TILE_EMPTY, new_k)

    # ---------------- BUILD_COOP / BUILD_PASTURE (435-445) --------------------
    new_k = torch.where(act & (op == O.OP_BUILD_COOP) & is_empty, O.TILE_COOP, new_k)
    new_k = torch.where(act & (op == O.OP_BUILD_PASTURE) & is_empty, O.TILE_PASTURE, new_k)

    # ---------------- PLACE (447-478) ----------------------------------------
    aidx = (a1 - O.ITEM_GOOSE).clamp(0, O.N_ANIMALS - 1)
    m_place = act & (op == O.OP_PLACE)
    m_pab = (m_place & (a1 >= O.ITEM_GOOSE) & (a1 < O.ITEM_GOOSE + O.N_ANIMALS)
             & (k == tab.animal_structure[aidx]))
    held = inv.gather(-1, item_i).squeeze(-1)
    m_pa = m_pab & (held > 0)
    _inv_take(inv, order, item_i, one, m_pa)
    new_k = torch.where(m_pa, O.TILE_ANIMAL, new_k)
    new_sp = torch.where(m_pa, aidx, new_sp)
    new_td = torch.where(m_pa, day, new_td)
    new_ty = torch.where(m_pa, 0, new_ty)
    new_tw = new_tw & ~m_pa
    new_tc = torch.where(m_pa, 0, new_tc)
    new_tm = torch.where(m_pa, 0, new_tm)
    new_tf = torch.where(m_pa, 0, new_tf)
    new_tcr = new_tcr & ~m_pa
    new_tfa = new_tfa & ~m_pa
    new_tcb = torch.where(m_pa, 0, new_tcb)

    # shed-drop branch: only when the animal branch did not fire at all
    nplace = torch.minimum(torch.minimum(a2, inv.gather(-1, item_i).squeeze(-1)), room)
    m_ps = m_place & ~m_pab & shed_adj & (a2 > 0) & item_ok & (nplace > 0)
    _inv_take(inv, order, item_i, nplace, m_ps)
    shed.scatter_add_(-1, item_i, torch.where(m_ps, nplace, 0).unsqueeze(-1))

    # ---------------- FEED (480-488) -----------------------------------------
    m_feed = (act & (op == O.OP_FEED) & is_animal & ~tw
              & (inv.gather(-1, wheat_i).squeeze(-1) > 0))
    _inv_take(inv, order, wheat_i, one, m_feed)
    new_tw = new_tw | m_feed

    # ---------------- COLLECT_FERTILIZER (490-497) ---------------------------
    m_cf = act & (op == O.OP_COLLECT_FERTILIZER) & is_animal & tfa
    new_tfa = new_tfa & ~m_cf
    _inv_add(inv, order, fert_i, one, m_cf, step)

    # ---------------- CARE (499-505) -----------------------------------------
    new_tcr = new_tcr | (act & (op == O.OP_CARE) & is_animal & ~tcr)

    # ---------------- clear payload whenever the tile became bare ------------
    bare = (new_k != k) & (new_k != O.TILE_ANIMAL) & (new_k != O.TILE_PLANT)
    new_sp = torch.where(bare, 0, new_sp)
    new_td = torch.where(bare, 0, new_td)
    new_ty = torch.where(bare, 0, new_ty)
    new_tw = new_tw & ~bare
    new_tc = torch.where(bare, 0, new_tc)
    new_tm = torch.where(bare, 0, new_tm)
    new_tf = torch.where(bare, 0, new_tf)
    new_tcr = new_tcr & ~bare
    new_tfa = new_tfa & ~bare
    new_tcb = torch.where(bare, 0, new_tcb)

    # ---------------- scatter the tile back ----------------------------------
    st.kind.scatter_(-1, flat, new_k.to(st.kind.dtype).unsqueeze(-1))
    st.species.scatter_(-1, flat, new_sp.to(st.species.dtype).unsqueeze(-1))
    st.tday.scatter_(-1, flat, new_td.to(st.tday.dtype).unsqueeze(-1))
    st.tyield.scatter_(-1, flat, new_ty.to(st.tyield.dtype).unsqueeze(-1))
    st.tflag.scatter_(-1, flat, new_tw.unsqueeze(-1))
    st.tcons.scatter_(-1, flat, new_tc.to(st.tcons.dtype).unsqueeze(-1))
    st.tmls.scatter_(-1, flat, new_tm.to(st.tmls.dtype).unsqueeze(-1))
    st.tfert.scatter_(-1, flat, new_tf.to(st.tfert.dtype).unsqueeze(-1))
    st.tcared.scatter_(-1, flat, new_tcr.unsqueeze(-1))
    st.tfavail.scatter_(-1, flat, new_tfa.unsqueeze(-1))
    st.tcare.scatter_(-1, flat, new_tcb.to(st.tcare.dtype).unsqueeze(-1))


# backwards-compatible alias
_apply_one_unit = apply_one_unit
