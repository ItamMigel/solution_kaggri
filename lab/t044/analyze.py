#!/usr/bin/env python3
"""T044 local replay attribution.  Replays are generated locally; never submits.

The hook records *successful* official-engine market commits, hires and land purchases.
It reports accounting flows, not a causal counterfactual: market prices are jointly set.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from collections import Counter, defaultdict
from pathlib import Path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as K
import kaggle_environments as KE


def _name(row, pid):
    # game_worker reverses the supplied paths when seat=1.
    return row["candidate"] if pid == (0 if row["seat"] == 0 else 1) else row["opponent"]


def mine_one(args):
    replay_path, row = args
    data = json.loads(Path(replay_path).read_text())
    cfg = dict(data["configuration"])
    cfg["seed"] = int(row["seed"])
    steps = data["steps"]
    current = {"step": 0, "day": 0}
    refs = {}
    events = [[], []]
    day_money = [[], []]
    original = (K._commit_unit, K._do_hire, K._do_buy_land, K.interpreter,
                KE.core.environments["kaggriculture"]["interpreter"])

    def commit(op, item, price, farm, private, market, *extra):
        pid = refs.get(id(farm), 0)
        money_before = float(farm["money"])
        inv_before = int(market["inventory"].get(item, 0))
        shed_before = int(private["shed"].get(item, 0))
        ok = original[0](op, item, price, farm, private, market, *extra)
        if ok:
            events[pid].append({"step": current["step"], "day": current["day"], "kind": "market",
                                "op": op, "item": item, "price": float(price),
                                "money_delta": float(farm["money"]) - money_before,
                                "market_before": inv_before,
                                "market_after": int(market["inventory"].get(item, 0)),
                                "shed_before": shed_before,
                                "shed_after": int(private["shed"].get(item, 0))})
        return ok

    def hire(farm, private, board_size, mult):
        pid = refs.get(id(farm), 0); before = float(farm["money"]); hands = len(farm["hands"])
        original[1](farm, private, board_size, mult)
        if len(farm["hands"]) > hands:
            events[pid].append({"step": current["step"], "day": current["day"], "kind": "hire",
                                "count": len(farm["hands"]) - hands,
                                "money_delta": float(farm["money"]) - before})

    def land(farm, board_size):
        pid = refs.get(id(farm), 0); before = float(farm["money"]); n = len(farm["unlocked_quadrants"])
        original[2](farm, board_size)
        if len(farm["unlocked_quadrants"]) > n:
            events[pid].append({"step": current["step"], "day": current["day"], "kind": "land",
                                "quadrant": farm["unlocked_quadrants"][-1],
                                "money_delta": float(farm["money"]) - before})

    def interp(state, env):
        farms = state[0].observation.farms
        if len(farms) >= 2:
            refs.clear(); refs.update({id(farms[0]): 0, id(farms[1]): 1})
        return original[3](state, env)

    K._commit_unit, K._do_hire, K._do_buy_land, K.interpreter = commit, hire, land, interp
    KE.core.environments["kaggriculture"]["interpreter"] = interp
    try:
        env = make("kaggriculture", configuration=cfg, debug=False); env.reset(2)
        for t in range(1, len(steps)):
            current["step"] = t; current["day"] = int(env.state[0]["observation"]["day"])
            farms = env.state[0]["observation"]["farms"]
            refs.clear(); refs.update({id(farms[0]): 0, id(farms[1]): 1})
            env.step([steps[t][p].get("action") or {} for p in range(2)])
            obs = env.steps[-1][0]["observation"]
            for p in range(2):
                day_money[p].append(float(obs["farms"][p]["money"]))
        final = [float(x.reward) for x in env.state]
    finally:
        K._commit_unit, K._do_hire, K._do_buy_land, K.interpreter = original[:4]
        KE.core.environments["kaggriculture"]["interpreter"] = original[4]
    return {"replay": Path(replay_path).name, "seed": row["seed"], "seat": row["seat"],
            "players": [_name(row, 0), _name(row, 1)], "final": final, "events": events,
            "money_steps": day_money}


def _flow(game, pid):
    out = defaultdict(float)
    for e in game["events"][pid]:
        if e["kind"] == "market":
            if e["op"] == "SELL": out["sale:" + e["item"]] += e["price"]
            else: out["buy:" + e["op"] + ":" + e["item"]] += e["money_delta"]
        else: out[e["kind"]] += e["money_delta"]
    out["initial"] = 3000.0
    out["final"] = game["final"][pid]
    out["residual"] = out["final"] - sum(v for k, v in out.items() if k not in ("final", "residual"))
    return dict(out)


def summarise(games):
    group = defaultdict(lambda: defaultdict(float))
    n = Counter()
    byday = defaultdict(lambda: defaultdict(float))
    contest = defaultdict(lambda: {"games": 0, "same_day": 0, "both_sell": 0, "price_gap_sum": 0.0, "price_gap_n": 0})
    for g in games:
        key = tuple(sorted(g["players"]))
        n[key] += 1
        for p, name in enumerate(g["players"]):
            for k, v in _flow(g, p).items(): group[(key, name)][k] += v
            for e in g["events"][p]:
                if e["kind"] == "market":
                    sign = 1 if e["op"] == "SELL" else -1
                    byday[(key, name, e["day"], e["op"], e["item"])]["units"] += 1
                    byday[(key, name, e["day"], e["op"], e["item"])]["cash"] += sign * e["price"]
                    byday[(key, name, e["day"], e["op"], e["item"])]["price_sum"] += e["price"]
        # Contested means both players successfully traded this good that day.  Keep SELL/Sell price gaps too.
        for day in range(30):
            for item in {e["item"] for es in g["events"] for e in es if e["kind"] == "market" and e["day"] == day}:
                a = [e for e in g["events"][0] if e["kind"] == "market" and e["day"] == day and e["item"] == item]
                b = [e for e in g["events"][1] if e["kind"] == "market" and e["day"] == day and e["item"] == item]
                if a and b:
                    q = contest[(key, item)]; q["same_day"] += 1
                    sa = [e["price"] for e in a if e["op"] == "SELL"]; sb = [e["price"] for e in b if e["op"] == "SELL"]
                    if sa and sb:
                        q["both_sell"] += 1; q["price_gap_sum"] += abs(sum(sa)/len(sa)-sum(sb)/len(sb)); q["price_gap_n"] += 1
        for item in {e["item"] for es in g["events"] for e in es if e["kind"] == "market"}:
            contest[(key, item)]["games"] += 1
    return {"games": len(games), "by_player_flow": [{"matchup": list(k[0]), "player": k[1], "games": n[k[0]], **dict(v)} for k,v in sorted(group.items())],
            "by_day_market": [{"matchup": list(k[0]), "player": k[1], "day": k[2], "op": k[3], "item": k[4], **dict(v)} for k,v in sorted(byday.items())],
            "contested": [{"matchup": list(k[0]), "item": k[1], **v, "sell_price_gap_mean": v["price_gap_sum"]/max(1,v["price_gap_n"])} for k,v in sorted(contest.items())]}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--run", required=True); ap.add_argument("--out", required=True); ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(); run = Path(a.run)
    rows = [json.loads(x) for x in (run / "games.jsonl").read_text().splitlines() if x]
    rows = [r for r in rows if "error" not in r and r.get("replay_path")]
    jobs = [(r["replay_path"], r) for r in rows]
    with mp.Pool(min(max(1,a.workers), 8)) as pool: games = list(pool.imap_unordered(mine_one, jobs))
    dest = Path(a.out); dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({"method": "official engine replay hooks; cash accounting, not causal counterfactual", "games": games, "summary": summarise(games)}, indent=2) + "\n")
    print(dest)

if __name__ == "__main__": main()
