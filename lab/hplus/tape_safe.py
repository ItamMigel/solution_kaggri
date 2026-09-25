"""Isolated, composable tape-safe in-place capabilities for Horizon+.

Unlike ``modules.build``, this builder deliberately owns a distinct ``_TS``
namespace, so it can be appended after the promoted es2_c1 source without
rebinding that source's ``_HP_BASE_AGENT`` closure.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT: dict[str, Any] = {
    "ts_on": False,
    "ts_day0": 0,
    "ts_day1": 29,
    "ts_ops": ["WATER", "FEED", "CARE"],
}
_ALLOWED = {"WATER", "FEED", "CARE"}

MODULE_SRC = r'''
# ================= Horizon+ isolated tape-safe capability (lab/hplus/tape_safe.py) =================
_TS = __TS_GENES__
_TS_STATS = {"fills": 0, "water": 0, "feed": 0, "care": 0, "skips": 0}

def _ts_op(tile, inv, allowed):
    """Return an immediately legal, in-place operation or None.

    The caller has already established that the parent chose PASS for this
    exact observed actor.  No movement, market command, inventory transfer or
    action index is changed.
    """
    if not isinstance(tile, dict):
        return None
    inv = inv or {}
    if tile.get("kind") == "PLANT":
        if "WATER" in allowed and not tile.get("watered_today"):
            return ["WATER"]
        return None
    if "animal" in tile:
        if "CARE" in allowed and not tile.get("cared_today"):
            return ["CARE"]
        if "FEED" in allowed and not tile.get("fed_today") and int(inv.get("WHEAT", 0)) > 0:
            return ["FEED"]
    return None

_TS_PARENT = agent
del agent

def agent(obs, config=None):
    action = _TS_PARENT(obs, config)
    if not _TS.get("ts_on"):
        return action
    try:
        step = int(obs["step"]); day = step // 24
        if not (int(_TS["ts_day0"]) <= day <= int(_TS["ts_day1"])) or step >= 718:
            return action
        seat = int(obs["player"]); farm = obs["farms"][seat]
        positions = [farm["farmer"], *(farm.get("hands") or [])]
        commands = [list(action.get("farmer") or ["PASS"]), *(list(c) for c in (action.get("hands") or []))]
        # Never pad a parent action: a mismatch can only be an incompatible
        # wrapper or an observation/action timing divergence, so abstain.
        if len(commands) != len(positions):
            _TS_STATS["skips"] += 1
            return action
        invs = (obs.get("private") or {}).get("inventories") or []
        allowed = set(_TS["ts_ops"])
        for i, (pos, command) in enumerate(zip(positions, commands)):
            if not command or command[0] != "PASS":
                continue
            x, y = int(pos[0]), int(pos[1])
            tile = farm["tiles"][y][x]
            op = _ts_op(tile, invs[i] if i < len(invs) else {}, allowed)
            if op is not None:
                commands[i] = op; _TS_STATS["fills"] += 1
                _TS_STATS[op[0].lower()] += 1
        return dict(action, farmer=commands[0], hands=commands[1:])
    except Exception:
        _TS_STATS["skips"] += 1
        return action
'''


def normalise(genes: dict[str, Any] | None) -> dict[str, Any]:
    if genes is None:
        genes = {}
    if not isinstance(genes, dict):
        raise ValueError("genes must be a dict")
    unknown = set(genes) - set(DEFAULT)
    if unknown:
        raise ValueError(f"unknown tape-safe genes: {sorted(unknown)}")
    value = dict(DEFAULT)
    value.update(genes)
    if type(value["ts_on"]) is not bool:
        raise ValueError("ts_on must be bool")
    if type(value["ts_day0"]) is not int or type(value["ts_day1"]) is not int:
        raise ValueError("day genes must be integers")
    if not (0 <= value["ts_day0"] <= value["ts_day1"] <= 29):
        raise ValueError("day window must be within 0..29")
    if not isinstance(value["ts_ops"], list) or not value["ts_ops"] or any(op not in _ALLOWED for op in value["ts_ops"]):
        raise ValueError("ts_ops must be a nonempty subset of WATER/FEED/CARE")
    return value


def build(base_main_py: str | Path, genes: dict[str, Any] | None, out_main_py: str | Path) -> dict[str, Any]:
    """Append the namespaced wrapper after any existing self-contained agent."""
    g = normalise(genes)
    base, out = Path(base_main_py), Path(out_main_py)
    text = base.read_text().rstrip() + "\n" + MODULE_SRC.replace("__TS_GENES__", repr(g))
    compile(text, str(out), "exec")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    info = {"base": str(base.resolve()), "genes": g, "default_off": not g["ts_on"]}
    out.with_suffix(out.suffix + ".tape_safe.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info
