#!/usr/bin/env python3
"""Replay-exact steep-item sale adjacency audit for T032; never submits."""
from __future__ import annotations

import argparse
import glob
import json
import multiprocessing as mp
from collections import defaultdict
from pathlib import Path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as K

TEAM = "misis biznessmenlb"
ITEMS = ("MILK", "WOOL", "STRAWBERRY", "MELON")
MIN_DUMP = {"MILK": 5, "WOOL": 5, "STRAWBERRY": 8, "MELON": 6}


def losses(root):
    result = []
    for path in sorted(glob.glob(str(Path(root) / "episode-*-replay.json"))):
        replay = json.loads(Path(path).read_text())
        teams, rewards = replay["info"]["TeamNames"], replay["rewards"]
        if TEAM in teams:
            us = teams.index(TEAM)
            if rewards[us] < rewards[1 - us]:
                result.append((path, us, replay["info"]["EpisodeId"], teams[1 - us]))
    if len(result) != 39:
        raise RuntimeError(f"expected exactly 39 losses, got {len(result)}")
    return result


def one(row):
    path, us, episode, opponent = row
    replay = json.loads(Path(path).read_text())
    cfg = dict(replay["configuration"]); cfg["seed"] = replay["info"]["seed"]
    events, refs, cur = [defaultdict(int), defaultdict(int)], {}, {"step": 0}
    commit0, interp0 = K._commit_unit, K.interpreter

    def commit(op, item, price, farm, private, market, *extra):
        ok = commit0(op, item, price, farm, private, market, *extra)
        if ok and op == "SELL" and item in ITEMS:
            events[refs[id(farm)]][(cur["step"], item)] += 1
        return ok

    def interp(state, env):
        farms = state[0].observation.farms
        refs.clear(); refs.update({id(farms[i]): i for i in range(len(farms))})
        return interp0(state, env)

    K._commit_unit, K.interpreter = commit, interp
    import kaggle_environments as ke
    old_registered = ke.core.environments["kaggriculture"]["interpreter"]
    ke.core.environments["kaggriculture"]["interpreter"] = interp
    try:
        env = make("kaggriculture", configuration=cfg, debug=False); env.reset(2)
        for step in range(1, len(replay["steps"])):
            cur["step"] = step
            refs.clear(); refs.update({id(env.state[0].observation.farms[i]): i for i in (0, 1)})
            env.step([replay["steps"][step][p].get("action") or {} for p in (0, 1)])
    finally:
        K._commit_unit, K.interpreter = commit0, interp0
        ke.core.environments["kaggriculture"]["interpreter"] = old_registered
    own, rival = events[us], events[1 - us]
    hits = []
    for (step, item), qty in rival.items():
        if qty < MIN_DUMP[item]:
            continue
        nearby = {dt: own.get((step + dt, item), 0) for dt in (-1, 0, 1)}
        hits.append({"step": step, "item": item, "opp_qty": qty, "own_before": nearby[-1],
                     "own_same": nearby[0], "own_after": nearby[1]})
    return {"episode": episode, "opponent": opponent, "dumps": hits}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays", default="/workspace/shared/replays/t028")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    if not 1 <= args.workers <= 8:
        ap.error("workers must be 1..8")
    rows = losses(args.replays)
    with mp.Pool(args.workers) as pool:
        games = list(pool.imap_unordered(one, rows))
    totals = defaultdict(int)
    for game in games:
        for dump in game["dumps"]:
            totals["dumps"] += 1; totals["dump_units"] += dump["opp_qty"]
            for key in ("own_before", "own_same", "own_after"):
                totals[key] += dump[key]
            totals["adjacent_dumps"] += int(bool(dump["own_before"] or dump["own_same"] or dump["own_after"]))
    result = {"method": "official-engine successful SELL hooks; dump=minimal same-step steep-item volume; adjacent=our successful same-item SELL at t-1/t/t+1",
              "losses": len(games), "thresholds": MIN_DUMP, "summary": dict(totals), "games": sorted(games, key=lambda x: x["episode"])}
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=False); out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
