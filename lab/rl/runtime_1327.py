"""Make the legacy residual-RL planner use kaggle-environments 1.32.7 economics.

The previous trainer is intentionally consumed as a read-only dependency from the
frozen research checkout.  Its batched planner predates the 1.32.7 price-curve
and town-demand changes, so using it unchanged would train the policy against a
different economy from :mod:`lab.gpuenv`.  ``apply`` patches only the planner's
runtime functions; it must be called before importing ``src.rl.train_real``.
"""
from __future__ import annotations

import math


_PATCHED = False


def _shape_scalar(func: str, x: float, T: float | None = None) -> float:
    x = max(0.0, x)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return math.sqrt(x)
    if func == "log":
        return math.log1p(x)
    if func == "log10":
        return math.log10(1.0 + x)
    if func == "hinge":
        if not T or T <= 0:
            return x
        u = x / T
        return u + 8.0 * max(0.0, u - 1.0) ** 2
    return x


def _shape_tensor(func, x, T=None):
    x = x.clamp_min(0.0)
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return x.sqrt()
    if func == "log":
        return x.log1p()
    if func == "log10":
        return (x + 1.0).log10()
    if func == "hinge":
        if not T or T <= 0:
            return x
        u = x / float(T)
        return u + 8.0 * (u - 1.0).clamp_min(0.0).square()
    return x


def apply() -> None:
    """Patch the imported legacy planner once, retaining its public API."""
    global _PATCHED
    if _PATCHED:
        return

    from src.rl import micro_real, micro_units, spec as S

    # 1.32.7 source defaults, verified by the full-state differential corpus.
    S.MARKET_PARAMS["CARROT"].update(bf="hinge", bt=1.00)
    S.MARKET_PARAMS["TOMATO"].update(bf="hinge", bt=0.40)
    S.MARKET_PARAMS["EGG"].update(bf="hinge", bt=0.40)
    S.CENTER_INTERVAL = 24
    S.CENTER_SCHEDULE = [(0, 1)]
    S._shape = _shape_scalar

    def price(item, inventory):
        p = S.MARKET_PARAMS[item]
        base, T = p["base"], p["T"]
        d = inventory - S.MARKET_I0
        if d >= 0:
            amp = p["at"] * base / _shape_scalar(p["af"], T, T)
            value = base - amp * _shape_scalar(p["af"], d, T)
        else:
            amp = p["bt"] * base / _shape_scalar(p["bf"], T, T)
            value = base + amp * _shape_scalar(p["bf"], -d, T)
        return max(S.PRICE_FLOOR, int(round(value)))

    S.price = price
    S.center_mult = lambda _day: 1

    def price_t(pi, inv):
        p = S.MARKET_PARAMS[S.PRODUCTS[pi]]
        d = inv.to(micro_real.torch.float64) - S.MARKET_I0
        above_amp = p["at"] * p["base"] / _shape_tensor(p["af"], d.new_tensor(p["T"]), p["T"])
        below_amp = p["bt"] * p["base"] / _shape_tensor(p["bf"], d.new_tensor(p["T"]), p["T"])
        above = p["base"] - above_amp * _shape_tensor(p["af"], d, p["T"])
        below = p["base"] + below_amp * _shape_tensor(p["bf"], -d, p["T"])
        return micro_real.torch.round(micro_real.torch.where(d >= 0, above, below)).clamp_min(
            float(S.PRICE_FLOOR)
        )

    micro_real._shape_t = _shape_tensor
    micro_units._shape_t = _shape_tensor
    micro_real.price_t = price_t
    micro_units.price_t = price_t
    _PATCHED = True
