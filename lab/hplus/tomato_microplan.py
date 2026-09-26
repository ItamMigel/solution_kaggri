"""G2: default-off, route-owned early tomato capability for frozen es5_c3g15.

The frozen parent has no native ``PLANT TOMATO`` tape action.  Its only tomato
route is V219: it buys land/seeds and plants ten cells on day 18, whose first
possible harvest is day 26.  The parent nevertheless retains one audited
opening alternative: at day 0 it replaces the second cow route with exactly
one tomato seed and its existing carrier's plant/water/service position.  This
module merely selects that already asserted route before the parent executes;
default-off is byte-identical and the parent restores the original tape each
episode.  It has no speculative order or free-moving worker.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT: dict[str, Any] = {"g2_on": False}

MODULE_SRC = r'''
# ================= Horizon+ G2 early-tomato route (lab/hplus/tomato_microplan.py) =================
_G2 = __G2_GENES__
_G2_REPORT = {"starts": 0, "seed_requests": 0, "mismatches": 0, "errors": 0}
_G2_PARENT = agent
del agent

def agent(obs, config=None):
    if not _G2.get("g2_on"):
        return _G2_PARENT(obs, config)
    try:
        # `_alt_install` in the frozen parent restores `_ALT_RAW` then asserts
        # every replaced d0..d2 action.  It is the route-ownership/mismatch
        # guard: a parent tape change raises there rather than silently
        # emitting a market-only tomato order.
        global _ALT_MODE
        prior = _ALT_MODE
        _ALT_MODE = "TomatoInsteadOfCow"
        try:
            action = _G2_PARENT(obs, config)
        finally:
            _ALT_MODE = prior
        if int(obs.get("step", -1)) == 0:
            # The final frozen opening layer replaces the inner route's market
            # list, so preserve its three certified orders and add precisely
            # the seed that the already-rewritten d0 plant consumes.  Fail
            # closed on a parent opening drift or a full order lane.
            orders = [list(order) for order in (action.get("market") or [])]
            expected = [["BUY_PRODUCT", "WHEAT", 8], ["SELL", "WHEAT", 3], ["BUY_SEED", "WHEAT", 1]]
            if orders != expected or len(orders) >= 10:
                _G2_REPORT["mismatches"] += 1
                return action
            action = dict(action, market=orders + [["BUY_SEED", "TOMATO", 1]])
            _G2_REPORT["seed_requests"] += 1
            _G2_REPORT["starts"] += 1
        return action
    except Exception:
        _G2_REPORT["errors"] += 1
        return _G2_PARENT(obs, config)
'''


def normalise(genes: dict[str, Any] | None) -> dict[str, Any]:
    genes = {} if genes is None else genes
    if not isinstance(genes, dict):
        raise ValueError("genes must be a dict")
    unknown = set(genes) - set(DEFAULT)
    if unknown:
        raise ValueError(f"unknown G2 genes: {sorted(unknown)}")
    result = dict(DEFAULT)
    result.update(genes)
    if type(result["g2_on"]) is not bool:
        raise ValueError("g2_on must be bool")
    return result


def build(base_main_py: str | Path, genes: dict[str, Any] | None, out_main_py: str | Path) -> dict[str, Any]:
    g = normalise(genes)
    base, out = Path(base_main_py), Path(out_main_py)
    text = base.read_text().rstrip() + "\n" + MODULE_SRC.replace("__G2_GENES__", repr(g))
    compile(text, str(out), "exec")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    info = {"base": str(base.resolve()), "genes": g, "default_off": not g["g2_on"],
            "route": "parent TomatoInsteadOfCow opening; one d0 plant replaces second cow"}
    out.with_suffix(out.suffix + ".tomato_microplan.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info
