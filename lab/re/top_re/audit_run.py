"""Trace top-RE plan execution around land purchases; diagnostic only.

Usage: python audit_run.py AGENT OPPONENT SEED SEAT OUT.json
The wrapped agent is unchanged; this records its observed input and returned
action before the official engine applies it.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from kaggle_environments import make


def load(path):
    ns = {"__name__": "top_re_audit_agent"}
    exec(compile(Path(path).read_text(), path, "exec"), ns)
    return ns


def empty_tiles(farm):
    return sum(tile is None for row in farm["tiles"] for tile in row)


def land_count(farm):
    return len(farm.get("unlocked_quadrants") or ["NW"])


def inspect(ns, obs, action):
    player = int(obs["player"])
    farm = obs["farms"][player]
    want = ns["plan_desired"](obs, player)
    unit_plan = ns["_unit_plan"](obs, player, want)
    plants = unit_plan["plant_targets"]
    crop_want_empty = Counter(
        role for (x, y), role in want.items()
        if ":" not in role and farm["tiles"][y][x] is None
    )
    cmds = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
    ops = [cmd[0] if cmd else "PASS" for cmd in cmds]
    return {
        "step": int(obs.get("step", 0)), "day": int(obs["day"]),
        "land": land_count(farm), "empty": empty_tiles(farm),
        "crop_want_empty": dict(crop_want_empty),
        "plant_targets": dict(Counter(plants.values())),
        "seed": dict((obs.get("private") or {}).get("seeds") or {}),
        "market": action.get("market") or [],
        "ops": dict(Counter(ops)), "units": len(ops),
        "moves": sum(op in {"NORTH", "SOUTH", "EAST", "WEST"} for op in ops),
        "plant_cmds": sum(op == "PLANT" for op in ops),
    }


def main(agent_path, opponent_path, seed, seat, out):
    ns = load(agent_path); real_agent = ns["agent"]
    records = []

    def wrapped(obs, config=None):
        action = real_agent(obs, config)
        records.append(inspect(ns, obs, action))
        return action

    agents = [wrapped, load(opponent_path)["agent"]]
    if seat:
        agents.reverse()
    env = make("kaggriculture", configuration={"seed": seed})
    env.run(agents)
    mine = int(seat)
    rewards = [float(s.reward or 0) for s in env.state]
    first = []
    previous = 1
    for row in records:
        if row["land"] > previous:
            first.append(row)
            previous = row["land"]
    band = [r for r in records if r["land"] >= 2 and 25 <= r["empty"] <= 40]
    all_ops = Counter(); units = moves = 0
    for row in records:
        all_ops.update(row["ops"]); units += row["units"]; moves += row["moves"]
    result = {
        "seed": seed, "seat": seat, "rewards": rewards,
        "mine": rewards[mine], "opp": rewards[1 - mine],
        "margin": rewards[mine] - rewards[1 - mine],
        "status": [str(s.status) for s in env.state],
        "land_events": first,
        "empty_band": {
            "turns": len(band),
            "mean_want_empty": (sum(sum(r["crop_want_empty"].values()) for r in band) / len(band)) if band else 0,
            "mean_plant_targets": (sum(sum(r["plant_targets"].values()) for r in band) / len(band)) if band else 0,
            "mean_plant_cmds": (sum(r["plant_cmds"] for r in band) / len(band)) if band else 0,
            "sample": band[:8],
        },
        "ops": dict(all_ops), "units": units, "moves": moves,
        "move_share": moves / units if units else 0,
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({k: result[k] for k in ("seed", "seat", "margin", "status", "move_share")}, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
