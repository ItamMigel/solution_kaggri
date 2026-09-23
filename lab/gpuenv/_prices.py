"""Exact market price table.

``market_price`` in the source is a pure function of (item, integer inventory),
so it is tabulated once -- in *pure Python, with the source's own arithmetic* --
which makes the GPU env bit-exact w.r.t. float rounding by construction (no
libm / SIMD-log discrepancy is possible).

Also builds the auxiliary prefix sums the closed-form market fast paths need:

* ``CUMSUM[i, v]``   = sum of P(i, u) for LO <= u < v          (stride 1)
* ``SUF2[i, v]``     = P(i, v) + P(i, v+2) + ... to the table end (stride 2)
* ``FLOOR_IDX[i]``   = smallest inventory v with P(i, v) == PRICE_FLOOR
                       (== HI+1 when the curve never reaches the floor)
"""

from __future__ import annotations

import math
import os

import numpy as np

from ._consts import MARKET_PARAMS, PRICE_FLOOR
from .ops import N_PRODUCTS

# Realistic inventories live in ~[8000, 12000]; this is deliberately far wider.
INV_LO = -20000
INV_HI = 60000
INV_N = INV_HI - INV_LO + 1

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cache")
_CACHE_PATH = os.path.join(_CACHE_DIR, f"prices_v2_{INV_LO}_{INV_HI}.npz")


def _shape(func: str, x: float, T: float | None = None) -> float:
    """Verbatim copy of the source's ``_shape``."""
    x = max(0.0, x)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return math.sqrt(x)
    if func == "log":
        return math.log(1.0 + x)
    if func == "log10":
        return math.log10(1.0 + x)
    if func == "hinge":
        # kaggle-environments 1.32.7: linear until x/T reaches one,
        # then a steep quadratic scarcity premium.  The source calls this
        # helper with T for both the numerator and normalising denominator.
        if not T or T <= 0:
            return x
        u = x / T
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def market_price(item: int, inventory: int) -> int:
    """Verbatim copy of the source's ``market_price`` (default params)."""
    base, I0, T, below_func, below_target, above_func, above_target = MARKET_PARAMS[item]
    if inventory < I0:
        amp = below_target * base / _shape(below_func, T, T)
        price = base + amp * _shape(below_func, I0 - inventory, T)
    else:
        amp = above_target * base / _shape(above_func, T)
        price = base - amp * _shape(above_func, inventory - I0)
    return max(PRICE_FLOOR, int(round(price)))


def _build_table() -> np.ndarray:
    table = np.empty((N_PRODUCTS, INV_N), dtype=np.int64)
    for item in range(N_PRODUCTS):
        base, I0, T, bf, bt, af, at = MARKET_PARAMS[item]
        amp_below = bt * base / _shape(bf, T, T)
        amp_above = at * base / _shape(af, T)
        row = table[item]
        for k in range(INV_N):
            inv = INV_LO + k
            if inv < I0:
                price = base + amp_below * _shape(bf, I0 - inv, T)
            else:
                price = base - amp_above * _shape(af, inv - I0)
            p = int(round(price))
            row[k] = p if p > PRICE_FLOOR else PRICE_FLOOR
    return table


def _load_table() -> np.ndarray:
    if os.path.exists(_CACHE_PATH):
        try:
            with np.load(_CACHE_PATH) as z:
                t = z["table"]
            if t.shape == (N_PRODUCTS, INV_N):
                return t
        except Exception:  # pragma: no cover - corrupt cache
            pass
    table = _build_table()
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        np.savez_compressed(_CACHE_PATH, table=table)
    except OSError:  # pragma: no cover
        pass
    return table


TABLE = _load_table()                                   # [9, INV_N] int64

# sum_{u < v} P(u).  Length INV_N + 1 so CUMSUM[:, INV_N] is the full sum.
CUMSUM = np.zeros((N_PRODUCTS, INV_N + 1), dtype=np.int64)
CUMSUM[:, 1:] = np.cumsum(TABLE, axis=1)

# stride-2 suffix sums: SUF2[v] = P(v) + SUF2[v+2].  Two extra slots of zeros so
# SUF2[v] for v in {INV_N, INV_N+1} is 0.  Each parity is an independent
# reversed cumulative sum.
SUF2 = np.zeros((N_PRODUCTS, INV_N + 2), dtype=np.int64)
for _par in (0, 1):
    _sl = TABLE[:, _par::2]
    SUF2[:, _par:INV_N:2] = np.cumsum(_sl[:, ::-1], axis=1)[:, ::-1]

# First inventory index (table coordinates) at which the price is at the floor.
FLOOR_IDX = np.full(N_PRODUCTS, INV_N, dtype=np.int64)
for _i in range(N_PRODUCTS):
    _hit = np.nonzero(TABLE[_i] <= PRICE_FLOOR)[0]
    if _hit.size:
        FLOOR_IDX[_i] = int(_hit[0])
