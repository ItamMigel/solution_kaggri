#!/usr/bin/env python3
"""T031: replay-exact WHEAT market timing audit, read-only and no Kaggle submit.

This deliberately reports two distinct quantities:
* observed trading cash-flow (all product-WHEAT buys vs all WHEAT sales);
* a *temporal* buy->later-sell match.  Products are fungible, so the latter
  is not a physical provenance claim when farms also harvest WHEAT.

For a price-pump diagnostic it also computes an accounting shadow price for
our BUY_PRODUCT WHEAT: keep every opponent WHEAT purchase in market inventory
while retaining the recorded rest of the tape.  It is a local price exposure,
not a feasible full-game counterfactual (opponent cash/shed would differ).
"""
from __future__ import annotations

import argparse
import glob
import json
import multiprocessing as mp
from collections import defaultdict, deque
from pathlib import Path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as K
import kaggle_environments as KE

TEAM = "misis biznessmenlb"
ITEM = "WHEAT"


def rows(replays, outcome="loss", expected=None):
    ans = []
    for raw in sorted(glob.glob(str(Path(replays) / "episode-*-replay.json"))):
        d = json.loads(Path(raw).read_text())
        names, rewards = d["info"]["TeamNames"], d["rewards"]
        if TEAM not in names:
            continue
        us = names.index(TEAM)
        won = rewards[us] > rewards[1 - us]
        lost = rewards[us] < rewards[1 - us]
        if outcome == "all" or (outcome == "loss" and lost) or (outcome == "win" and won):
            ans.append((raw, us, d["info"]["EpisodeId"], names[1-us]))
    if expected is not None and len(ans) != expected:
        raise RuntimeError(f"expected {expected} {outcome} replays, got {len(ans)}")
    return ans


def _price(item, inv, market):
    return K.market_price(item, inv, market.get("params"))


def mine(row):
    path, us, episode, opponent = row
    d = json.loads(Path(path).read_text())
    cfg = dict(d["configuration"]); cfg["seed"] = d["info"]["seed"]
    steps = d["steps"]
    cur = {"step": 0, "day": 0, "seq": 0}
    refs, events, towns = {}, [[], []], []

    oc, ou, oe = K._commit_unit, K._apply_unit_action, K._end_of_day
    ot, oi = K._town_consume, K.interpreter
    old_core_interp = KE.core.environments["kaggriculture"]["interpreter"]

    def commit(op, item, price, farm, private, market, *extra):
        pid = refs.get(id(farm), 0)
        before_i = market["inventory"].get(item, 0)
        before_s = private["shed"].get(item, 0)
        ok = oc(op, item, price, farm, private, market, *extra)
        if ok and item == ITEM and op in ("SELL", "BUY_PRODUCT"):
            cur["seq"] += 1
            events[pid].append({"step": cur["step"], "day": cur["day"], "seq": cur["seq"],
                                "op": op, "price": price, "market_before": before_i,
                                "market_after": market["inventory"][item], "shed_before": before_s,
                                "shed_after": private["shed"].get(item, 0)})
        return ok

    def unit(farm, private, idx, action, board_size, day, turns, shed_capacity=100):
        pid = refs.get(id(farm), 0)
        inv = private["inventories"][idx] if idx < len(private["inventories"]) else {}
        b_inv, b_shed = inv.get(ITEM, 0), private["shed"].get(ITEM, 0)
        pos = farm["farmer"] if idx == 0 else farm["hands"][idx - 1]
        tile = farm["tiles"][pos[1]][pos[0]]
        crop = tile.get("crop") if isinstance(tile, dict) else None
        ou(farm, private, idx, action, board_size, day, turns, shed_capacity)
        inv2 = private["inventories"][idx] if idx < len(private["inventories"]) else {}
        a_inv, a_shed = inv2.get(ITEM, 0), private["shed"].get(ITEM, 0)
        op = action[0] if isinstance(action, list) and action else "?"
        if op in ("PICKUP", "DROP", "HARVEST", "FEED", "FERTILIZE") and (b_inv != a_inv or b_shed != a_shed):
            cur["seq"] += 1
            events[pid].append({"step": cur["step"], "day": cur["day"], "seq": cur["seq"],
                                "op": op, "price": None, "crop": crop, "inv_delta": a_inv-b_inv,
                                "shed_delta": a_shed-b_shed})

    def eod(state, env, day):
        # Only record aggregate movement, preserving that the engine drops all
        # hand inventories to shed at the boundary.
        before = [sum(x.get("WHEAT", 0) for x in s.observation.private["inventories"])
                  for s in state]
        oe(state, env, day)
        for pid, s in enumerate(state):
            moved = before[pid]
            if moved:
                cur["seq"] += 1
                events[pid].append({"step": cur["step"], "day": day, "seq": cur["seq"],
                                    "op": "EOD_DROP", "price": None, "inv_delta": -moved,
                                    "shed_delta": moved})

    def town(env, state, step):
        m = state[0].observation.market
        bi, bp = m["inventory"][ITEM], m["prices"][ITEM]
        ot(env, state, step)
        ai, ap = m["inventory"][ITEM], m["prices"][ITEM]
        if ai != bi:
            towns.append({"step": cur["step"], "day": cur["day"], "before_inv": bi,
                          "after_inv": ai, "before_price": bp, "after_price": ap})

    def interp(state, env):
        # `make` can replace observation objects; rebind immediately before
        # every official interpreter call, as replay_mine does.
        fs = state[0].observation.farms
        if len(fs) >= 2:
            refs.clear(); refs.update({id(fs[0]): 0, id(fs[1]): 1})
        return oi(state, env)

    K._commit_unit, K._apply_unit_action, K._end_of_day, K._town_consume, K.interpreter = commit, unit, eod, town, interp
    KE.core.environments["kaggriculture"]["interpreter"] = interp
    try:
        env = make("kaggriculture", configuration=cfg, debug=False); env.reset(2)
        for t in range(1, len(steps)):
            cur.update(step=t, day=env.state[0]["observation"]["day"], seq=0)
            fs = env.state[0]["observation"]["farms"]
            refs.clear(); refs.update({id(fs[0]): 0, id(fs[1]): 1})
            env.step([steps[t][p].get("action") or {} for p in range(2)])
    finally:
        K._commit_unit, K._apply_unit_action, K._end_of_day, K._town_consume, K.interpreter = oc, ou, oe, ot, oi
        KE.core.environments["kaggriculture"]["interpreter"] = old_core_interp
    return {"episode": episode, "opponent": opponent, "us": us, "events": events, "town": towns}


def _temporal(buys, sells):
    """FIFO cash-flow matching only: each buy is matched to a later sale."""
    q, matches = deque(), []
    for e in sorted([*buys, *sells], key=lambda x: (x["step"], x["seq"])):
        if e["op"] == "BUY_PRODUCT": q.append(e)
        else:
            while q:
                b = q.popleft()
                if (e["step"], e["seq"]) > (b["step"], b["seq"]):
                    matches.append((b, e)); break
    return matches


def game_summary(g):
    us, op = g["us"], 1-g["us"]
    pe = g["events"][op]; ue = g["events"][us]
    buy = [e for e in pe if e["op"] == "BUY_PRODUCT"]
    sell = [e for e in pe if e["op"] == "SELL"]
    ours = [e for e in ue if e["op"] == "BUY_PRODUCT"]
    use = [e for e in pe if e["op"] == "FERTILIZE"]
    matched = _temporal(buy, sell)
    # Conservative inter-turn price exposure: remove a purchase only while it
    # is outstanding until the FIFO-matched later sale.  We deliberately apply
    # changes after the whole turn, because same-iteration lockstep quotes are
    # simultaneous and cannot pump the other player's price.
    matched_sale = {(s["step"], s["seq"]): b for b, s in matched}
    starts = defaultdict(int); ends = defaultdict(int)
    for b, s in matched:
        starts[b["step"]] += 1; ends[s["step"]] += 1
    held = 0; extra = 0.0
    by_step = defaultdict(list)
    for e in ours: by_step[e["step"]].append(e)
    for step in sorted(set(starts) | set(ends) | set(by_step)):
        # Purchases/sales made this turn take effect only next turn here.
        for e in by_step[step]:
            cf = _price(ITEM, e["market_before"] - 1 + held, {"params": {}})
            extra += e["price"] - cf
        held += starts[step] - ends[step]
    first_town_after = []
    for b, s in matched:
        t = next((x for x in g["town"] if x["step"] >= b["step"]), None)
        first_town_after.append(None if t is None else t["after_price"] - b["price"])
    return {"episode": g["episode"], "opponent": g["opponent"],
            "opp_buy_units": len(buy), "opp_buy_cost": sum(e["price"] for e in buy),
            "opp_sell_units": len(sell), "opp_sell_revenue": sum(e["price"] for e in sell),
            "cashflow_wheat": sum(e["price"] for e in sell)-sum(e["price"] for e in buy),
            "buy_mean_price": sum((e["price"] for e in buy), 0)/max(1,len(buy)),
            "sell_mean_price": sum((e["price"] for e in sell), 0)/max(1,len(sell)),
            "buy_mean_day": sum((e["day"] for e in buy), 0)/max(1,len(buy)),
            "sell_mean_day": sum((e["day"] for e in sell), 0)/max(1,len(sell)),
            "temporal_match_units": len(matched),
            "temporal_match_pnl": sum(s["price"]-b["price"] for b,s in matched),
            "temporal_match_mean_hold_steps": sum(s["step"]-b["step"] for b,s in matched)/max(1,len(matched)),
            "town_price_delta_after_buy_mean": sum(x for x in first_town_after if x is not None)/max(1,sum(x is not None for x in first_town_after)),
            "our_buy_units": len(ours), "our_buy_cost": sum(e["price"] for e in ours),
            "our_buy_mean_price": sum((e["price"] for e in ours), 0)/max(1,len(ours)),
            "our_interturn_shadow_extra_cost": extra,
            "opp_use_units": sum(max(0, -int(e.get("inv_delta", 0))) for e in use),
            "opp_use_wheat": sum(max(0, -int(e.get("inv_delta", 0))) for e in use if e.get("crop") == "WHEAT"),
            "opp_use_carrot": sum(max(0, -int(e.get("inv_delta", 0))) for e in use if e.get("crop") == "CARROT")}


def mean(a, k): return sum(x[k] for x in a)/len(a)

def report(out):
    games = out["games"]
    return "\n".join([
        f"# T031 — {ITEM} buy/sell time audit", "",
        f"Exact {len(games)} {out.get('outcome', 'selected')} replays, official engine 1.32.7. `temporal_match` is FIFO cash-flow matching of a purchase to a later sale, not physical provenance: {ITEM} is fungible and farms may also create it. `shadow_extra` holds opponent purchases in shared inventory only; it is a local price-exposure accounting diagnostic, not a feasible behaviour counterfactual.", "",
        f"| per-{out.get('outcome', 'selected')} replay mean | value |", "|---|---:|",
        *[f"| {k} | {mean(games,k):,.2f} |" for k in ("opp_buy_units","opp_buy_cost","opp_sell_units","opp_sell_revenue","cashflow_wheat","buy_mean_price","sell_mean_price","buy_mean_day","sell_mean_day","temporal_match_units","temporal_match_pnl","temporal_match_mean_hold_steps","town_price_delta_after_buy_mean","our_buy_units","our_buy_cost","our_buy_mean_price","our_interturn_shadow_extra_cost","opp_use_units","opp_use_wheat","opp_use_carrot")],
        "", "## Per opponent identity", "",
        "| opponent | games | opp buy $ | opp sale $ | cash-flow $ | FIFO later-sale P&L $ | buy d | sell d | our shadow cost $ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        *[f"| {name} | {len(xs)} | {mean(xs,'opp_buy_cost'):,.0f} | {mean(xs,'opp_sell_revenue'):,.0f} | {mean(xs,'cashflow_wheat'):,.0f} | {mean(xs,'temporal_match_pnl'):,.0f} | {mean(xs,'buy_mean_day'):.1f} | {mean(xs,'sell_mean_day'):.1f} | {mean(xs,'our_interturn_shadow_extra_cost'):,.1f} |" for name,xs in sorted(_groups(games).items())],
        "", "Raw per-game values are in the adjacent JSON.", ""])


def _groups(games):
    d=defaultdict(list)
    for g in games: d[g["opponent"]].append(g)
    return d


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",required=True); ap.add_argument("--replays",default="/workspace/shared/replays/t028"); ap.add_argument("--workers",type=int,default=8); ap.add_argument("--item",default="WHEAT",choices=("WHEAT","FERTILIZER")); ap.add_argument("--outcome",default="loss",choices=("loss","win","all")); ap.add_argument("--expect",type=int); args=ap.parse_args()
    if not 1 <= args.workers <= 8: ap.error("workers must be 1..8")
    global ITEM
    ITEM = args.item
    selected = rows(args.replays, args.outcome, args.expect)
    with mp.Pool(args.workers) as p: raw=list(p.imap_unordered(mine, selected))
    games=[game_summary(g) for g in sorted(raw,key=lambda x:x["episode"])]
    out={"method":"official replay hooks; cash-flow and price shadow qualified in report", "item": ITEM, "outcome": args.outcome, "games":games}
    dest=Path(args.out)
    if dest.exists() or dest.with_suffix(".md").exists():
        raise FileExistsError(f"refusing to overwrite existing result: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    dest.with_suffix(".md").write_text(report(out))
    print(dest.with_suffix(".md"))

if __name__=="__main__": main()
