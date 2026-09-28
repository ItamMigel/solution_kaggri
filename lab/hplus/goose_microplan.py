"""G1: audited early-goose route microplan for the frozen es5_c3g15 base.

The gene means the number of geese *placed by the early route*: 4, 5 or 6.
It is deliberately not a naked market overlay. Every replacement has a
corresponding parent BUILD_PASTURE, PICKUP and PLACE action at the same actor,
turn and tile. A parent-action/state mismatch disables all later rewrites.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT: dict[str, Any] = {"g1_on": False, "g1_target": 4}


MODULE_SRC = r'''
# ================= Horizon+ G1 early goose microplan (lab/hplus/goose_microplan.py) =================
_G1 = __G1_GENES__
_G1_REPORT = {"started": 0, "completed": 0, "rewrites": 0, "mismatches": 0, "mismatch_step": -1,
              "confirmed_sites": 0, "service_fills": 0, "egg_sale_units": 0, "errors": 0}
_G1_STATE = {}

# Verified against es5_c3g15 on two held-out worlds. Each tuple is
# (actor-index; 0=farmer, 1+=hand, exact parent command). Target 4 converts
# the complete opening 2-COW + 2-SHEEP route. Target 5 adds d2's COW route;
# target 6 adds d3's COW route. The existing parent actions retain all moves,
# service and drop scheduling; only species/structure are changed.
_G1_STEPS = {
    4: {
        2: ((1, ("PICKUP", "COW")), (5, ("PICKUP", "COW"))),
        3: ((0, ("PICKUP", "SHEEP")), (5, ("BUILD_PASTURE",))),
        4: ((1, ("BUILD_PASTURE",)), (5, ("PLACE", "COW"))),
        5: ((1, ("PLACE", "COW")),),
        6: ((5, ("PICKUP", "SHEEP")),),
        7: ((0, ("BUILD_PASTURE",)),),
        8: ((0, ("PLACE", "SHEEP")),),
        9: ((5, ("BUILD_PASTURE",)),),
        10: ((5, ("PLACE", "SHEEP")),),
    },
    5: {33: ((2, ("BUILD_PASTURE",)),), 65: (),
        66: ((0, ("PICKUP", "COW")),), 69: ((0, ("PLACE", "COW")),)},
    6: {88: ((1, ("BUILD_PASTURE",)),), 92: ((3, ("PICKUP", "COW")),),
        95: ((3, ("PLACE", "COW")),)},
}

def _g1_market(step, market, target):
    want = []
    if step == 1:
        want = [("COW", 2), ("SHEEP", 2)]
    elif target >= 5 and step == 65:
        want = [("COW", 1)]
    elif target >= 6 and step == 88:
        want = [("COW", 1)]
    if not want:
        return market, True
    copied = [list(order) for order in (market or [])]
    found = [(order[1], int(order[2])) for order in copied
             if len(order) >= 3 and order[0] == "BUY_ANIMAL" and order[1] in ("COW", "SHEEP")]
    if sorted(found) != sorted(want):
        return market, False
    for order in copied:
        if len(order) >= 3 and order[0] == "BUY_ANIMAL" and (order[1], int(order[2])) in want:
            order[1] = "GOOSE"
    return copied, True

def _g1_expected(step, target):
    out = []
    for threshold in (4, 5, 6):
        if target >= threshold:
            out.extend(_G1_STEPS[threshold].get(step, ()))
    return out

def _g1_matches(actual, expected):
    """Allow the inherited species layer's already-equivalent GOOSE rewrite."""
    if tuple(actual) == expected:
        return True
    return (expected[0] in ("PICKUP", "PLACE") and len(actual) >= 2
            and actual[0] == expected[0] and actual[1] in ("COW", "SHEEP", "GOOSE")
            and tuple(actual[2:]) == expected[2:])

def _g1_rewrite(step, obs, action, st):
    target = int(_G1["g1_target"])
    market, market_ok = _g1_market(step, action.get("market"), target)
    expected = _g1_expected(step, target)
    units = [list(action.get("farmer") or ["PASS"])] + [list(cmd) for cmd in (action.get("hands") or [])]
    # All exact parent action checks happen before any current-turn mutation.
    if not market_ok or any(index >= len(units) or not _g1_matches(units[index], command)
                            for index, command in expected):
        st["broken"] = True; _G1_REPORT["mismatches"] += 1; _G1_REPORT["mismatch_step"] = step
        return action
    if step == 1:
        st["started"] = True; _G1_REPORT["started"] += 1
    if not st.get("started"):
        return action
    positions = [obs["farms"][int(obs["player"])]["farmer"]] + list(obs["farms"][int(obs["player"])].get("hands") or [])
    for index, command in expected:
        replacement = list(command)
        if command[0] == "BUILD_PASTURE":
            replacement = ["BUILD_COOP"]
        else:
            replacement[1] = "GOOSE"
            if command[0] == "PLACE" and index < len(positions):
                st["pending"].append((int(positions[index][0]), int(positions[index][1]), step // 24))
        units[index] = replacement; _G1_REPORT["rewrites"] += 1
    rewritten = dict(action, market=market, farmer=units[0], hands=units[1:])
    terminal = 95 if target >= 6 else 69 if target >= 5 else 10
    if step == terminal:
        _G1_REPORT["completed"] += 1
    return rewritten

def _g1_confirm_and_sell(obs, action, st):
    """Credit only observed G1-goose harvests; sell only in a parent sale slot."""
    seat, step = int(obs["player"]), int(obs["step"])
    farm = obs["farms"][seat]
    keep = []
    for x, y, day in st["pending"]:
        tile = farm["tiles"][y][x]
        if isinstance(tile, dict) and tile.get("animal") == "GOOSE" and tile.get("placed_day") == day:
            st["sites"].add((x, y)); _G1_REPORT["confirmed_sites"] += 1
        elif step // 24 <= day:
            keep.append((x, y, day))
    st["pending"] = keep
    positions = [farm["farmer"]] + list(farm.get("hands") or [])
    units = [list(action.get("farmer") or ["PASS"])] + [list(command) for command in (action.get("hands") or [])]
    inventories = (obs.get("private") or {}).get("inventories") or []
    for index, (pos, command) in enumerate(zip(positions, units)):
        x, y = int(pos[0]), int(pos[1]); tile = farm["tiles"][y][x]
        # The parent is allowed to retain every non-PASS operation. A PASS on
        # an observed G1 tile is the one safe idle slot the microplan owns.
        if command == ["PASS"] and (x, y) in st["sites"] and isinstance(tile, dict) and tile.get("animal") == "GOOSE":
            inv = inventories[index] if index < len(inventories) else {}
            if int(tile.get("yield_units", 0)) > 0:
                units[index] = ["HARVEST"]
            elif not tile.get("fed_today") and int(inv.get("WHEAT", 0)) > 0:
                units[index] = ["FEED"]
            elif not tile.get("cared_today"):
                units[index] = ["CARE"]
            elif tile.get("fertilizer_available"):
                units[index] = ["COLLECT_FERTILIZER"]
            if units[index] != ["PASS"]:
                command = units[index]; _G1_REPORT["service_fills"] += 1
        if command == ["HARVEST"] and (x, y) in st["sites"] and isinstance(tile, dict) and tile.get("animal") == "GOOSE":
            st["credit"] += max(0, int(tile.get("yield_units", 0)))
    action = dict(action, farmer=units[0], hands=units[1:])
    market = [list(order) for order in (action.get("market") or [])]
    if st["credit"] and any(len(order) >= 3 and order[0] == "SELL" for order in market):
        try:
            stock = projected_shed(action, FarmView(obs))
            planned = sum(max(0, int(order[2])) for order in market if len(order) >= 3 and order[:2] == ["SELL", "EGG"])
            extra = min(st["credit"], max(0, int(stock.get("EGG", 0)) - planned))
            if extra and len(market) < 10:
                market.append(["SELL", "EGG", extra]); st["credit"] -= extra
                _G1_REPORT["egg_sale_units"] += extra
                return dict(action, market=market)
        except Exception:
            _G1_REPORT["errors"] += 1
    return action

_G1_PARENT = agent
del agent

def agent(obs, config=None):
    if not _G1.get("g1_on"):
        return _G1_PARENT(obs, config)
    try:
        action = _G1_PARENT(obs, config)
        seat, step = int(obs["player"]), int(obs["step"])
        st = _G1_STATE.get(seat)
        if st is None or step <= st.get("last", -1):
            st = _G1_STATE[seat] = {"last": -1, "started": False, "broken": False,
                                    "pending": [], "sites": set(), "credit": 0}
        st["last"] = step
        if st["broken"]:
            return action
        action = _g1_rewrite(step, obs, action, st)
        if st["broken"]:
            return _G1_PARENT(obs, config)
        return _g1_confirm_and_sell(obs, action, st)
    except Exception:
        _G1_REPORT["errors"] += 1
        return _G1_PARENT(obs, config)
'''


def normalise(genes: dict[str, Any] | None) -> dict[str, Any]:
    if genes is None:
        genes = {}
    if not isinstance(genes, dict):
        raise ValueError("genes must be a dict")
    unknown = set(genes) - set(DEFAULT)
    if unknown:
        raise ValueError(f"unknown G1 genes: {sorted(unknown)}")
    value = dict(DEFAULT)
    value.update(genes)
    if type(value["g1_on"]) is not bool:
        raise ValueError("g1_on must be bool")
    if value["g1_target"] not in (4, 5, 6):
        raise ValueError("g1_target must be one of 4, 5, 6")
    return value


def build(base_main_py: str | Path, genes: dict[str, Any] | None, out_main_py: str | Path) -> dict[str, Any]:
    """Append G1 after frozen es5_c3g15, retaining its COLLECT wrapper."""
    g = normalise(genes)
    base, out = Path(base_main_py), Path(out_main_py)
    text = base.read_text().rstrip() + "\n" + MODULE_SRC.replace("__G1_GENES__", repr(g))
    compile(text, str(out), "exec")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    info = {"base": str(base.resolve()), "genes": g, "default_off": not g["g1_on"]}
    out.with_suffix(out.suffix + ".goose_microplan.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info
