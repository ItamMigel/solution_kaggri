"""T031 default-off market-only WHEAT timing layer for sealed es6.

The enabled layer may append one WHEAT market order only.  It never modifies
``farmer`` or ``hands`` and abstains whenever the parent already trades WHEAT.
Its conservative buy is a cheap early feed reserve; its sale is a capped trim
only above a physical WHEAT reserve.  Default-off returns the parent action
object unchanged, making byte/action identity auditable.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT: dict[str, Any] = {
    "wm_on": False,
    "wm_buy_day0": 6, "wm_buy_day1": 17, "wm_buy_price_max": 30,
    "wm_feed_floor": 20, "wm_buy_cap": 8, "wm_cash_reserve": 2000,
    "wm_sell_day0": 10, "wm_sell_day1": 28, "wm_sell_price_min": 40,
    "wm_sell_reserve": 35, "wm_sell_cap": 8,
}

MODULE_SRC = r'''
# ================= T031 market-only WHEAT timing layer (lab/hplus/wheat_market.py) =================
_WM = __WM_GENES__
_WM_PARENT = agent
del agent
_WM_STATS = {"buy_turns": 0, "buy_units": 0, "sell_turns": 0, "sell_units": 0,
             "abstain_parent_wheat": 0, "abstain_slots": 0, "errors": 0}

def agent(obs, config=None):
    action = _WM_PARENT(obs, config)
    if not _WM["wm_on"]:
        return action
    try:
        # No unit-action authority: only make a shallow action copy after a
        # fully qualified market decision; inherited farmer/hands stay intact.
        step = int(obs["step"]); day = step // 24
        if not 0 <= day <= 29 or step >= 718:
            return action
        market = action.get("market") or []
        if len(market) >= 10:
            _WM_STATS["abstain_slots"] += 1
            return action
        if any(isinstance(o, list) and len(o) >= 2 and o[1] == "WHEAT" and o[0] in ("SELL", "BUY_PRODUCT") for o in market):
            _WM_STATS["abstain_parent_wheat"] += 1
            return action
        player = int(obs["player"])
        private = obs.get("private") or {}
        shed = private.get("shed") or {}
        held = max(0, int(shed.get("WHEAT", 0)))
        room = max(0, 100 - sum(max(0, int(v)) for v in shed.values()))
        price = max(1, int((obs.get("market") or {}).get("prices", {}).get("WHEAT", 1)))
        money = max(0, int(obs["farms"][player]["money"]))
        order = None
        # Early cheap physical feed reserve.  The cap/room/cash checks are
        # explicit because BUY_PRODUCT deposits directly into the shared shed.
        if (int(_WM["wm_buy_day0"]) <= day <= int(_WM["wm_buy_day1"]) and price <= int(_WM["wm_buy_price_max"]) and held < int(_WM["wm_feed_floor"])):
            q = min(int(_WM["wm_buy_cap"]), int(_WM["wm_feed_floor"]) - held, room,
                    max(0, (money - int(_WM["wm_cash_reserve"])) // price))
            if q > 0:
                order = ["BUY_PRODUCT", "WHEAT", q]
                _WM_STATS["buy_turns"] += 1; _WM_STATS["buy_units"] += q
        # Only sell owned physical surplus; never replace a parent sale.
        if order is None and (int(_WM["wm_sell_day0"]) <= day <= int(_WM["wm_sell_day1"]) and price >= int(_WM["wm_sell_price_min"]) and held > int(_WM["wm_sell_reserve"])):
            q = min(int(_WM["wm_sell_cap"]), held - int(_WM["wm_sell_reserve"]))
            if q > 0:
                order = ["SELL", "WHEAT", q]
                _WM_STATS["sell_turns"] += 1; _WM_STATS["sell_units"] += q
        if order is None:
            return action
        result = dict(action)
        result["market"] = [list(o) if isinstance(o, list) else o for o in market] + [order]
        return result
    except Exception:
        _WM_STATS["errors"] += 1
        return action

agent.telemetry = _WM_STATS
'''


def normalise(genes: dict[str, Any] | None) -> dict[str, Any]:
    value = dict(DEFAULT); value.update(genes or {})
    if set(value) != set(DEFAULT):
        raise ValueError("unknown wheat-market gene")
    if type(value["wm_on"]) is not bool or any(type(value[k]) is not int for k in value if k != "wm_on"):
        raise ValueError("invalid wheat-market gene types")
    if not (0 <= value["wm_buy_day0"] <= value["wm_buy_day1"] <= 29 and 0 <= value["wm_sell_day0"] <= value["wm_sell_day1"] <= 29):
        raise ValueError("day windows must be 0..29")
    if min(value[k] for k in value if k != "wm_on") < 0:
        raise ValueError("numeric genes must be non-negative")
    return value


def build(base_main_py: str | Path, genes: dict[str, Any] | None, out_main_py: str | Path) -> dict[str, Any]:
    genes = normalise(genes)
    base, out = Path(base_main_py), Path(out_main_py)
    src = base.read_text().rstrip() + "\n" + MODULE_SRC.replace("__WM_GENES__", repr(genes))
    compile(src, str(out), "exec")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(src)
    info = {"base": str(base.resolve()), "genes": genes, "default_off": not genes["wm_on"]}
    out.with_suffix(out.suffix + ".wheat_market.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info
