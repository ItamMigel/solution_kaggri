"""Composable route-conditioned second-land wrapper for Horizon+.

The parent ``modules.build`` owns the debt-confirmed land helper.  This module
only decides when that helper may run: after the day-six router selected the
non-Yarn EXP240 expert, and only while the second quadrant is outstanding.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT: dict[str, Any] = {
    "rl_on": False,
    "rl_expert": "EXP240",
    "rl_land_k": 48,
    "rl_buffer": 300,
}

MODULE_SRC = r'''
# ================ Horizon+ isolated route-conditioned land (lab/hplus/route_land.py) ================
_RL = __RL_GENES__
_RL_STATS = {"calls": 0, "matched": 0, "skips": 0}


def _rl_state(obs):
    seat = int(obs["player"])
    return (_IMPL.chassis.players.get(seat) or {}), seat


def _rl_should_call(obs):
    """Allow only the EXP240 second-land acceleration and its debt cleanup.

    ``_hp_land`` records an early purchase one step later, then removes exactly
    one parent BUY_LAND.  We must keep calling it while that confirmation/debt
    is pending, even after the farm has reached three quadrants.  A third-land
    acceleration is intentionally out of scope.
    """
    state, seat = _rl_state(obs)
    router = state.get("router_state") or {}
    if router.get("expert") != _RL["rl_expert"]:
        return False
    land_state = _HP_LAND.get(seat) or {}
    reconciling = land_state.get("pending") is not None or int(land_state.get("owed", 0)) > 0
    quadrants = len(obs["farms"][seat].get("unlocked_quadrants") or [])
    return reconciling or quadrants == 2


_RL_PARENT = agent
del agent


def agent(obs, config=None):
    action = _RL_PARENT(obs, config)
    if not _RL.get("rl_on"):
        return action
    try:
        _RL_STATS["calls"] += 1
        if _rl_should_call(obs):
            _RL_STATS["matched"] += 1
            # Reuse the parent helper and its confirmed debt accounting, while
            # supplying this experiment's acceleration only for this call.
            old_k, old_buffer = _HP["land_k"], _HP["land_buffer"]
            _HP["land_k"], _HP["land_buffer"] = _RL["rl_land_k"], _RL["rl_buffer"]
            try:
                return _hp_land(obs, action)
            finally:
                _HP["land_k"], _HP["land_buffer"] = old_k, old_buffer
        return action
    except Exception:
        _RL_STATS["skips"] += 1
        return action
'''


def normalise(genes: dict[str, Any] | None) -> dict[str, Any]:
    if genes is None:
        genes = {}
    if not isinstance(genes, dict):
        raise ValueError("genes must be a dict")
    unknown = set(genes) - set(DEFAULT)
    if unknown:
        raise ValueError(f"unknown route-land genes: {sorted(unknown)}")
    value = dict(DEFAULT)
    value.update(genes)
    if type(value["rl_on"]) is not bool:
        raise ValueError("rl_on must be bool")
    if value["rl_expert"] != "EXP240":
        raise ValueError("only the evidence-backed EXP240 condition is allowed")
    if type(value["rl_land_k"]) is not int or value["rl_land_k"] not in (48, 72):
        raise ValueError("rl_land_k must be 48 (d9) or 72 (d8)")
    if type(value["rl_buffer"]) not in (int, float) or not 0 <= value["rl_buffer"] <= 1000:
        raise ValueError("rl_buffer must be in [0, 1000]")
    return value


def build(base_main_py: str | Path, genes: dict[str, Any] | None, out_main_py: str | Path) -> dict[str, Any]:
    """Append this namespaced layer after a parent built by ``modules.build``."""
    g = normalise(genes)
    base, out = Path(base_main_py), Path(out_main_py)
    text = base.read_text().rstrip() + "\n" + MODULE_SRC.replace("__RL_GENES__", repr(g))
    compile(text, str(out), "exec")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    info = {"base": str(base.resolve()), "genes": g, "default_off": not g["rl_on"]}
    out.with_suffix(out.suffix + ".route_land.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info
