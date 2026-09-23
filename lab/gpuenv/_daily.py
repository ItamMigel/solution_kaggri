"""Batched town consumption, plant decay and end-of-day refresh
(source lines 696-859)."""

from __future__ import annotations

import torch

from . import ops as O
from . import _mt19937 as MT
from ._consts import (BOARD_SIZE, N_SHOPS, N_TILES, SHED_CAPACITY,
                      TOWN_CENTER_SELL_INTERVAL, TOWN_SHOP_SELL_INTERVAL,
                      TOWN_SHOP_UNLOCK_INTERVAL, TURNS_PER_DAY, WEED_SPAWN_CHANCE,
                      town_center_mult)
from ._tables import get_tables
from ._units import _ORDER_SENTINEL

# n.bit_length() for n in 0..8
_BITLEN = [0, 1, 2, 2, 3, 3, 3, 3, 4]
_CHOICE_TRIES = 48


def _clear_tiles(st, mask):
    """Reduce a tile to a bare kind (all payload fields zeroed)."""
    z = torch.zeros((), dtype=st.species.dtype, device=st.species.device)
    st.species.copy_(torch.where(mask, z, st.species))
    st.tday.copy_(torch.where(mask, z.to(st.tday.dtype), st.tday))
    st.tyield.copy_(torch.where(mask, z.to(st.tyield.dtype), st.tyield))
    st.tflag.copy_(torch.where(mask, torch.zeros_like(st.tflag), st.tflag))
    st.tcons.copy_(torch.where(mask, z.to(st.tcons.dtype), st.tcons))
    st.tmls.copy_(torch.where(mask, z.to(st.tmls.dtype), st.tmls))
    st.tfert.copy_(torch.where(mask, z.to(st.tfert.dtype), st.tfert))
    st.tcared.copy_(torch.where(mask, torch.zeros_like(st.tcared), st.tcared))
    st.tfavail.copy_(torch.where(mask, torch.zeros_like(st.tfavail), st.tfavail))
    st.tcare.copy_(torch.where(mask, z.to(st.tcare.dtype), st.tcare))


# --------------------------------------------------------------------------- #
def town_consume(st, step, day=None):
    """Source 696-718.

    ``step`` may be a Python int (host-driven) or a 0-dim device tensor, in which
    case the two demand ticks are gated by device-side masks so the whole phase
    is static-shaped and CUDA-graph capturable.
    """
    tab = get_tables(str(st.money.device))
    # (int64 matmul is unimplemented on CUDA; 8x9 broadcast is cheap anyway)
    shop_pull = (st.shops.to(torch.int64).unsqueeze(-1)
                 * tab.shop_demand.unsqueeze(0)).sum(1)
    if not torch.is_tensor(step):
        if step % TOWN_SHOP_SELL_INTERVAL == 0:
            st.market_inv -= shop_pull
        if step % TOWN_CENTER_SELL_INTERVAL == 0:
            st.market_inv -= tab.town_center_mask
        return
    if day is None:
        day = step // TURNS_PER_DAY
    shop_tick = (step % TOWN_SHOP_SELL_INTERVAL == 0).to(torch.int64)
    center_tick = (step % TOWN_CENTER_SELL_INTERVAL == 0).to(torch.int64)
    st.market_inv -= (shop_tick * shop_pull
                      + center_tick * tab.town_center_mask)


def decay_plants(st, step):
    """Source 721-735.  ``step``: Python int or 0-dim device tensor."""
    m = ((st.kind == O.TILE_PLANT) & (st.tmls >= 0) & (step >= st.tmls)
         & (((step - st.tmls) % 2) == 0))
    st.tyield.copy_(st.tyield - m.to(st.tyield.dtype))
    to_weed = m & (st.tyield <= 0)
    st.kind.copy_(torch.where(to_weed, torch.full_like(st.kind, O.TILE_WEED), st.kind))
    _clear_tiles(st, to_weed)


# --------------------------------------------------------------------------- #
def _refresh_plants(st, day: int):
    """Source 738-771."""
    tab = get_tables(str(st.money.device))
    next_day = day + 1
    is_p = st.kind == O.TILE_PLANT
    was_watered = st.tflag & is_p

    cons = torch.where(was_watered, torch.zeros_like(st.tcons), st.tcons + 1)
    st.tcons.copy_(torch.where(is_p, cons, st.tcons))
    st.tflag.copy_(torch.where(is_p, torch.zeros_like(st.tflag), st.tflag))
    to_weed = is_p & (st.tcons >= 2)

    sp = st.species.to(torch.int64).clamp(0, O.N_CROPS - 1)
    ongoing = tab.crop_ongoing[sp]
    interval = tab.crop_interval[sp].clamp(min=1)
    max_yield = tab.crop_max_yield[sp]
    dsf = next_day - st.tday.to(torch.int64) - tab.crop_first_yield[sp]
    cont = is_p & ~to_weed & ongoing
    prod = cont & (dsf >= 0) & ((dsf % interval) == 0)
    pc = dsf // interval + 1
    prod = prod & (pc <= max_yield)
    fertilized = was_watered & (st.tfert >= day)
    gain = torch.where(fertilized, torch.full_like(dsf, 2), torch.ones_like(dsf))
    new_y = torch.minimum(max_yield, st.tyield.to(torch.int64) + gain)
    st.tyield.copy_(torch.where(prod, new_y.to(st.tyield.dtype), st.tyield))
    last = prod & (pc == max_yield)
    st.tmls.copy_(torch.where(last,
                              ((next_day + 1) * TURNS_PER_DAY) * torch.ones_like(st.tmls),
                              st.tmls))

    st.kind.copy_(torch.where(to_weed, torch.full_like(st.kind, O.TILE_WEED), st.kind))
    _clear_tiles(st, to_weed)


def _refresh_animals(st, day: int):
    """Source 774-802."""
    tab = get_tables(str(st.money.device))
    next_day = day + 1
    is_a = st.kind == O.TILE_ANIMAL
    fed = st.tflag & is_a

    cons = torch.where(fed, torch.zeros_like(st.tcons), st.tcons + 1)
    st.tcons.copy_(torch.where(is_a, cons, st.tcons))
    escape = is_a & (st.tcons >= 2)
    alive = is_a & ~escape

    sp = st.species.to(torch.int64).clamp(0, O.N_ANIMALS - 1)
    interval = tab.animal_interval[sp]
    max_held = tab.animal_max_held[sp]
    dsf = next_day - st.tday.to(torch.int64) - tab.animal_first_yield[sp]
    prod = alive & (dsf >= 0) & ((dsf % interval) == 0)
    bonus = torch.where(fed, st.tcare.to(torch.int64), torch.zeros_like(dsf))
    new_y = torch.minimum(max_held, st.tyield.to(torch.int64) + 1 + bonus)
    st.tyield.copy_(torch.where(prod, new_y.to(st.tyield.dtype), st.tyield))
    st.tcare.copy_(torch.where(prod, torch.zeros_like(st.tcare), st.tcare))

    banked = alive & st.tcared & fed
    st.tcare.copy_(torch.where(banked, st.tcare + 1, st.tcare))
    st.tfavail.copy_(torch.where(alive, torch.ones_like(st.tfavail), st.tfavail))
    st.tflag.copy_(torch.where(alive, torch.zeros_like(st.tflag), st.tflag))
    st.tcared.copy_(torch.where(alive, torch.zeros_like(st.tcared), st.tcared))

    struct = tab.animal_structure[sp].to(st.kind.dtype)
    st.kind.copy_(torch.where(escape, struct, st.kind))
    _clear_tiles(st, escape)


def _spawn_weeds(st, doubles):
    """Source 805-809.  ``doubles``: [B, >=200] float64 for this day.

    The rng stream is consumed per *empty* tile, player 0's board first, so a
    player-1 tile's draw index is offset by player 0's empty-tile count.
    """
    empty = st.kind == O.TILE_EMPTY                       # [B, 2, 100]
    e = empty.to(torch.int64)
    rank = e.cumsum(-1) - e                               # exclusive scan
    n0 = e[:, 0].sum(-1)                                  # [B]
    offset = torch.stack([torch.zeros_like(n0), n0], dim=1).unsqueeze(-1)
    idx = (rank + offset).clamp(0, doubles.shape[1] - 1)
    d = doubles.unsqueeze(1).expand(-1, 2, -1).gather(-1, idx)
    spawn = empty & (d < WEED_SPAWN_CHANCE)
    st.kind.copy_(torch.where(spawn, torch.full_like(st.kind, O.TILE_WEED), st.kind))
    return n0 + e[:, 1].sum(-1)                           # words consumed / 2


def _drop_inventories(st):
    """Source 812-826: every unit inventory into the shed, in list order then
    dict-insertion order, with the shed cap destroying the overflow."""
    b, p, u, n_items = st.inv.shape
    unit_idx = torch.arange(u, device=st.inv.device).view(1, 1, u, 1)
    key = unit_idx * (1 << 44) + st.inv_order
    key = key.reshape(b, p, u * n_items)
    n = st.inv.reshape(b, p, u * n_items)
    perm = torch.argsort(key, dim=-1, stable=True)
    n_sorted = n.gather(-1, perm)
    cum_excl = n_sorted.cumsum(-1) - n_sorted
    room = (SHED_CAPACITY - st.shed.sum(-1)).clamp(min=0).unsqueeze(-1)
    take = (room - cum_excl).clamp_(min=0).minimum(n_sorted)
    item_of = (torch.arange(u * n_items, device=st.inv.device) % n_items).view(1, 1, -1)
    item_sorted = item_of.expand(b, p, -1).gather(-1, perm)
    st.shed.scatter_add_(-1, item_sorted, take)
    st.inv.zero_()
    st.inv_order.fill_(_ORDER_SENTINEL)


def _unlock_shop(st, words, base_word, enabled=True):
    """Source 855-859: ``rng.choice(sorted(SHOPS))`` with replacement.

    ``enabled``: bool or 0-dim device tensor -- whether this is an unlock day.
    Gating on device keeps the end-of-day phase static-shaped for graph capture.
    """
    tab = get_tables(str(st.shops.device))
    # 1.32.7 permits repeated unlocks.  The town holds at most 8 *instances*,
    # so the count tensor must not be reduced to the old boolean set.
    do = (st.shops.sum(-1) < 8) & torch.as_tensor(enabled, device=st.shops.device)
    k = torch.full_like(st.shops.sum(-1), 4)  # _randbelow(8) -> getrandbits(4)
    idx = base_word.unsqueeze(-1) + torch.arange(_CHOICE_TRIES, device=words.device)
    idx = idx.clamp(0, words.shape[1] - 1)
    cand = words.gather(-1, idx) >> (32 - k).unsqueeze(-1)
    valid = cand < N_SHOPS
    pos = torch.where(valid, torch.arange(_CHOICE_TRIES, device=words.device).expand_as(valid),
                      torch.full_like(cand, _CHOICE_TRIES)).min(dim=-1).values
    r = cand.gather(-1, pos.clamp(max=_CHOICE_TRIES - 1).unsqueeze(-1)).squeeze(-1)

    pick = torch.nn.functional.one_hot(r, num_classes=N_SHOPS).to(st.shops.dtype)
    st.shops.add_(pick * do.unsqueeze(-1).to(st.shops.dtype))


def end_of_day(st, day, max_hands: int, words=None, unlock=None):
    """Source 829-859.

    ``day``   : Python int or 0-dim device tensor.
    ``words`` : [B, W] raw MT19937 stream for this day; taken from the
                precomputed ``st.rng_words`` buffer when omitted.
    ``unlock``: bool / 0-dim device tensor overriding the host-side
                ``next_day % townShopUnlockInterval == 0`` test, so the whole
                phase can be captured once and replayed for any day.
    """
    if words is None:
        if torch.is_tensor(day):
            words = st.rng_words.index_select(1, day.reshape(1)).squeeze(1)
        else:
            words = st.rng_words[:, day]
    if words.shape[-1] < MT.WORDS_PER_DAY:
        raise RuntimeError(
            "end_of_day needs the day's MT19937 stream: rng_words is only "
            f"{words.shape[-1]} words wide (rng_lazy env must pass words=...)")
    words = words.to(torch.int64) & 0xFFFFFFFF                    # [B, W]
    doubles = MT.words_to_doubles(words)                          # [B, W//2]

    _refresh_plants(st, day)
    _refresh_animals(st, day)
    n_draws = _spawn_weeds(st, doubles)
    _drop_inventories(st)

    # farmer back to the default spawn, hands dismissed
    st.ux.fill_(BOARD_SIZE // 2 - 1)
    st.uy.fill_(BOARD_SIZE // 2 - 1)
    st.n_hands.zero_()
    st.hires_today.zero_()

    if unlock is None:
        next_day = day + 1
        unlock = bool(next_day > 0 and next_day % TOWN_SHOP_UNLOCK_INTERVAL == 0)
        if not unlock:
            return
    _unlock_shop(st, words, 2 * n_draws, unlock)
