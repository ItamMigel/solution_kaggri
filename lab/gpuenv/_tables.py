"""Per-device constant tensors (built once, cached)."""

from __future__ import annotations

from functools import lru_cache
from types import SimpleNamespace

import torch

from . import _consts as C
from . import _prices as P


@lru_cache(maxsize=8)
def get_tables(device_str: str) -> SimpleNamespace:
    dev = torch.device(device_str)

    def i32(x):
        return torch.tensor(x, dtype=torch.int32, device=dev)

    def i64(x):
        return torch.tensor(x, dtype=torch.int64, device=dev)

    t = SimpleNamespace()
    # crops (indexed by crop/item id 0..4)
    t.crop_seed_cost = i64(C.CROP_SEED_COST)
    t.crop_first_yield = i64(C.CROP_FIRST_YIELD_DAY)
    t.crop_max_yield_day = i64(C.CROP_MAX_YIELD_DAY)
    t.crop_interval = i64(C.CROP_INTERVAL)
    t.crop_max_yield = i64(C.CROP_MAX_YIELD)
    t.crop_ongoing = torch.tensor(C.CROP_ONGOING, dtype=torch.bool, device=dev)
    t.crop_window_start = i64(C.CROP_WATER_WINDOW_START)

    # animals (indexed by animal idx 0..2)
    t.animal_cost = i64(C.ANIMAL_COST)
    t.animal_structure = i64(C.ANIMAL_STRUCTURE)
    t.animal_first_yield = i64(C.ANIMAL_FIRST_YIELD_DAY)
    t.animal_interval = i64(C.ANIMAL_INTERVAL)
    t.animal_max_held = i64(C.ANIMAL_MAX_HELD)
    t.animal_product = i64(C.ANIMAL_PRODUCT)

    t.move_dx = i64(C.MOVE_DX)
    t.move_dy = i64(C.MOVE_DY)

    t.land_prices = i64(C.LAND_PRICES)
    t.quadrant_mask = torch.tensor(C.QUADRANT_MASK, dtype=torch.bool, device=dev)
    t.land_quadrant = i64(C.LAND_ORDER_QUADRANT)
    t.shed_access_flat = i64(C.SHED_ACCESS_FLAT)

    t.shop_demand = i64(C.SHOP_DEMAND)              # [8, 9]
    t.town_center_mask = i64(C.TOWN_CENTER_MASK)    # [9]

    t.fib = i64(C.FIB)
    # n.bit_length() for n in 0..8 (rng.choice's _randbelow)
    t.bitlen = i64([0, 1, 2, 2, 3, 3, 3, 3, 4])

    # market price tables
    t.price = torch.as_tensor(P.TABLE, device=dev)          # [9, INV_N] int64
    t.price_cumsum = torch.as_tensor(P.CUMSUM, device=dev)  # [9, INV_N+1]
    t.price_suf2 = torch.as_tensor(P.SUF2, device=dev)      # [9, INV_N+2]
    t.price_floor_idx = torch.as_tensor(P.FLOOR_IDX, device=dev)  # [9]
    t.inv_lo = P.INV_LO
    t.inv_n = P.INV_N
    return t


def price_of(tab, item: torch.Tensor, inventory: torch.Tensor) -> torch.Tensor:
    """``market_price(item, inventory)`` for arbitrary broadcast shapes (int64)."""
    idx = (inventory - tab.inv_lo).clamp_(0, tab.inv_n - 1)
    return tab.price[item.clamp(0, 8), idx]
