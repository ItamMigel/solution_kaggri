"""T030 default-off, in-place WHEAT planting gene for a sealed Horizon agent.

It has no pathing, hiring, market order or inventory-transfer authority.  When
enabled it can only spend a seed already visible in private state on an empty,
unlocked tile occupied by an actor whose inherited command is exactly PASS.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT: dict[str, Any] = {"wi_on": False, "wi_day0": 0, "wi_day1": 29}

MODULE_SRC = r'''
# ================= T030 idle-WHEAT tape-safe gene (lab/hplus/wheat_idle.py) =================
_WI = __WI_GENES__
_WI_STATS = {"plants": 0, "abstain_shape": 0, "abstain_seed": 0, "errors": 0}
_WI_PARENT = agent
del agent

def agent(obs, config=None):
    action = _WI_PARENT(obs, config)
    if not _WI.get("wi_on"):
        return action
    try:
        step = int(obs["step"]); day = step // 24
        if not (int(_WI["wi_day0"]) <= day <= int(_WI["wi_day1"])) or step >= 718:
            return action
        seat = int(obs["player"]); farm = obs["farms"][seat]
        positions = [farm["farmer"], *(farm.get("hands") or [])]
        commands = [list(action.get("farmer") or ["PASS"]), *(list(c) for c in (action.get("hands") or []))]
        # Never add a hand command or mutate a non-PASS inherited command.
        if len(commands) != len(positions):
            _WI_STATS["abstain_shape"] += 1
            return action
        private = obs.get("private") or {}
        seeds = int((private.get("seeds") or {}).get("WHEAT", 0))
        committed = sum(1 for command in commands if command[:2] == ["PLANT", "WHEAT"])
        spare = max(0, seeds - committed)
        if not spare:
            _WI_STATS["abstain_seed"] += 1
            return action
        for i, (pos, command) in enumerate(zip(positions, commands)):
            if not spare or command != ["PASS"]:
                continue
            x, y = int(pos[0]), int(pos[1])
            # `None` specifically excludes structures, crops, animals, weeds
            # and LOCKED tiles. The engine will consume one existing seed.
            if farm["tiles"][y][x] is None:
                commands[i] = ["PLANT", "WHEAT"]
                spare -= 1
                _WI_STATS["plants"] += 1
        return dict(action, farmer=commands[0], hands=commands[1:])
    except Exception:
        _WI_STATS["errors"] += 1
        return action
'''


def normalise(genes: dict[str, Any] | None) -> dict[str, Any]:
    value = dict(DEFAULT)
    value.update(genes or {})
    if set(value) != set(DEFAULT):
        raise ValueError("unknown wheat-idle gene")
    if type(value["wi_on"]) is not bool or any(type(value[x]) is not int for x in ("wi_day0", "wi_day1")):
        raise ValueError("invalid wheat-idle gene types")
    if not 0 <= value["wi_day0"] <= value["wi_day1"] <= 29:
        raise ValueError("wheat-idle window must be 0..29")
    return value


def build(base_main_py: str | Path, genes: dict[str, Any] | None, out_main_py: str | Path) -> dict[str, Any]:
    genes = normalise(genes)
    base, out = Path(base_main_py), Path(out_main_py)
    src = base.read_text().rstrip() + "\n" + MODULE_SRC.replace("__WI_GENES__", repr(genes))
    compile(src, str(out), "exec")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(src)
    info = {"base": str(base.resolve()), "genes": genes, "default_off": not genes["wi_on"]}
    out.with_suffix(out.suffix + ".wheat_idle.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info
