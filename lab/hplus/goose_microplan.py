"""Bounded early-goose capability for Horizon+.

G1 converts Horizon's two *opening* cows into geese by rewriting the complete
existing route (buy, BUILD_PASTURE, PICKUP, PLACE, service and sale).  It does
not append a naked market buy, which would strand a goose in the shed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT: dict[str, Any] = {
    "g1_on": False,
    # This first certified leg converts exactly two opening cows.  The parent
    # route has no later goose placements on this family, so target 4/5/6
    # honestly requires new placement/service routes rather than a parameter.
    "g1_target": 2,
}


MODULE_SRC = r'''
# ================= Horizon+ G1 early goose microplan (lab/hplus/goose_microplan.py) =================
_G1 = __G1_GENES__
_G1_REPORT = {"opening_started": 0, "opening_completed": 0, "rewrites": 0,
              "mismatches": 0, "errors": 0}
_G1_STATE = {}

# Callback step -> {actor index: exact parent command to replace}.  Actor zero
# is farmer; 1+ are existing tape hands.  The selected sites are built before
# the cow purchases and are subsequently PICKUP/PLACE'd by the same frozen
# opening route.  Later generic animal service sees either animal type.
_G1_UNITS = {
    2: {1: ["PICKUP", "COW"], 5: ["PICKUP", "COW"]},
    3: {5: ["BUILD_PASTURE"]},
    # Once the first coop is observed, the inherited species layer may already
    # change hand 5's PLACE to GOOSE.  That is the same intended action, so
    # accept it; hand 1's structure rewrite remains required.
    4: {1: ["BUILD_PASTURE"]},
    5: {},
}

def _g1_rewrite_opening(step, action, state):
    """Rewrite only the verified five opening turns, else leave parent intact.

    Each later mutation is conditional on the exact parent command.  The
    sequence has no added actor, movement, market slot, or unit turn: its two
    coops occupy the same two pasture coordinates and both existing carriers
    retain their routes.  A mismatch is observable telemetry, never a guessed
    replacement.
    """
    if step == 1:
        market = [list(o) for o in (action.get("market") or [])]
        cows = [o for o in market if len(o) >= 3 and o[:2] == ["BUY_ANIMAL", "COW"] and int(o[2]) == 2]
        if len(cows) != 1:
            state["broken"] = True; _G1_REPORT["mismatches"] += 1
            return action
        cows[0][1] = "GOOSE"
        state["started"] = True; _G1_REPORT["opening_started"] += 1; _G1_REPORT["rewrites"] += 1
        return dict(action, market=market)
    expected = _G1_UNITS.get(step)
    if expected is None or not state.get("started") or state.get("broken"):
        return action
    units = [list(action.get("farmer") or ["PASS"])] + [list(c) for c in (action.get("hands") or [])]
    if any(i >= len(units) or units[i] != cmd for i, cmd in expected.items()):
        state["broken"] = True; _G1_REPORT["mismatches"] += 1
        return action
    if step == 4 and (len(units) <= 5 or units[5][:1] != ["PLACE"] or units[5][1:2] not in (["COW"], ["GOOSE"])):
        state["broken"] = True; _G1_REPORT["mismatches"] += 1
        return action
    if step == 5 and (len(units) <= 1 or units[1][:1] != ["PLACE"] or units[1][1:2] not in (["COW"], ["GOOSE"])):
        state["broken"] = True; _G1_REPORT["mismatches"] += 1
        return action
    for i, cmd in expected.items():
        units[i] = (["BUILD_COOP"] if cmd == ["BUILD_PASTURE"] else [cmd[0], "GOOSE"] + cmd[2:])
        _G1_REPORT["rewrites"] += 1
    if step == 4 and units[5][1] == "COW":
        units[5] = ["PLACE", "GOOSE"] + units[5][2:]; _G1_REPORT["rewrites"] += 1
    if step == 5 and units[1][1] == "COW":
        units[1] = ["PLACE", "GOOSE"] + units[1][2:]; _G1_REPORT["rewrites"] += 1
    if step == 5:
        _G1_REPORT["opening_completed"] += 1
    return dict(action, farmer=units[0], hands=units[1:])

_G1_PARENT = agent
del agent

def agent(obs, config=None):
    if not _G1.get("g1_on"):
        return _G1_PARENT(obs, config)
    try:
        action = _G1_PARENT(obs, config)
        seat, step = int(obs["player"]), int(obs["step"])
        state = _G1_STATE.get(seat)
        if state is None or step <= state.get("last", -1):
            state = _G1_STATE[seat] = {"last": -1, "started": False, "broken": False}
        state["last"] = step
        return _g1_rewrite_opening(step, action, state)
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
    if value["g1_target"] != 2:
        raise ValueError("only certified target 2 is implemented; 4/5/6 need a new route")
    return value


def build(base_main_py: str | Path, genes: dict[str, Any] | None, out_main_py: str | Path) -> dict[str, Any]:
    """Append G1 after any frozen self-contained Horizon candidate."""
    g = normalise(genes)
    base, out = Path(base_main_py), Path(out_main_py)
    text = base.read_text().rstrip() + "\n" + MODULE_SRC.replace("__G1_GENES__", repr(g))
    compile(text, str(out), "exec")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    info = {"base": str(base.resolve()), "genes": g, "default_off": not g["g1_on"]}
    out.with_suffix(out.suffix + ".goose_microplan.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info
