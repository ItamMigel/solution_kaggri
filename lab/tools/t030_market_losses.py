"""Read-only market decomposition for the 39 es3_g5 ladder losses in replays/t028.

Replays are re-executed in isolated worker processes through replay_mine's
official-engine hooks.  The output distinguishes realised SELL price from
quantity/production; it makes no counterfactual causal claim.
"""
from __future__ import annotations

import argparse
import glob
import json
import multiprocessing as mp
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replay_mine import mine  # noqa: E402

TEAM = "misis biznessmenlb"
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")


def loss_paths(root: str):
    rows = []
    for path in sorted(glob.glob(str(Path(root) / "episode-*-replay.json"))):
        replay = json.load(open(path))
        teams, rewards = replay["info"]["TeamNames"], replay["rewards"]
        if TEAM not in teams:
            continue
        us = teams.index(TEAM)
        if rewards[us] < rewards[1 - us]:
            rows.append((path, us, replay["info"]["EpisodeId"], teams[1-us], rewards[us] - rewards[1-us]))
    return rows


def worker(row):
    path, us, episode, opponent, margin = row
    r = mine(path, verbose=False)
    return dict(result=r, us=us, episode=episode, opponent=opponent, margin=margin)


def avg(pair):
    return pair[1] / pair[0] if pair[0] else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays", default="/workspace/shared/replays/t028")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    rows = loss_paths(args.replays)
    if len(rows) != 39:
        raise SystemExit(f"expected exactly 39 losses, found {len(rows)}")
    with mp.Pool(args.workers) as pool:
        games = list(pool.imap_unordered(worker, rows))
    crop = {p: {"games_both": 0, "us_first": 0, "opp_first": 0, "same_day": 0,
                "us_units": 0, "opp_units": 0, "us_revenue": 0.0, "opp_revenue": 0.0,
                "same_day_sale_games": 0} for p in PRODUCTS}
    per_day = defaultdict(lambda: {"us_units": 0, "opp_units": 0, "us_revenue": 0.0, "opp_revenue": 0.0,
                                    "us_first": 0, "opp_first": 0, "same_day": 0, "both_games": 0})
    opponent_summary = defaultdict(lambda: {"games": 0, "margin": 0.0, "revenue_gap": 0.0, "unit_gap": 0})
    details = []
    for game in games:
        r, us = game["result"], game["us"]
        op = 1 - us
        own_sells, opp_sells = r["sells"][us], r["sells"][op]
        own_days, opp_days = r["sell_by_day"][us], r["sell_by_day"][op]
        own_first, opp_first = r["first_sell_day"][us], r["first_sell_day"][op]
        gross_us = sum(x[1] for x in own_sells.values()); gross_op = sum(x[1] for x in opp_sells.values())
        opponent_summary[game["opponent"]]["games"] += 1
        opponent_summary[game["opponent"]]["margin"] += game["margin"]
        opponent_summary[game["opponent"]]["revenue_gap"] += gross_us - gross_op
        opponent_summary[game["opponent"]]["unit_gap"] += sum(x[0] for x in own_sells.values()) - sum(x[0] for x in opp_sells.values())
        entry = {"episode": game["episode"], "opponent": game["opponent"], "margin": game["margin"],
                 "gross_sell_us": gross_us, "gross_sell_opp": gross_op, "shops": r["tiles_hist"][-1][6], "items": {}}
        for item in PRODUCTS:
            a, b = own_sells.get(item, [0, 0.0]), opp_sells.get(item, [0, 0.0])
            if not a[0] and not b[0]:
                continue
            first_a, first_b = own_first.get(item), opp_first.get(item)
            item_entry = {"us_units": a[0], "opp_units": b[0], "us_price": avg(a), "opp_price": avg(b),
                          "us_first_day": first_a, "opp_first_day": first_b}
            entry["items"][item] = item_entry
            c = crop[item]; c["us_units"] += a[0]; c["opp_units"] += b[0]; c["us_revenue"] += a[1]; c["opp_revenue"] += b[1]
            if first_a is not None and first_b is not None:
                c["games_both"] += 1
                if first_a < first_b: c["us_first"] += 1
                elif first_b < first_a: c["opp_first"] += 1
                else: c["same_day"] += 1
            overlap = set(own_days).intersection(opp_days)
            for day in overlap:
                ua, oa = own_days[day].get(item, 0), opp_days[day].get(item, 0)
                if not (ua or oa):
                    continue
                d = per_day[(item, int(day))]
                d["us_units"] += ua; d["opp_units"] += oa; d["both_games"] += int(ua > 0 and oa > 0)
                pa = [p for it, p in r["sell_price_by_day"][us].get(day, []) if it == item]
                pb = [p for it, p in r["sell_price_by_day"][op].get(day, []) if it == item]
                d["us_revenue"] += sum(pa); d["opp_revenue"] += sum(pb)
                if ua and oa:
                    c["same_day_sale_games"] += 1
        details.append(entry)
    for item, row in crop.items():
        row["us_avg_price"] = avg([row["us_units"], row["us_revenue"]])
        row["opp_avg_price"] = avg([row["opp_units"], row["opp_revenue"]])
        row["revenue_gap_us_minus_opp"] = row["us_revenue"] - row["opp_revenue"]
        row["unit_gap_us_minus_opp"] = row["us_units"] - row["opp_units"]
    day_rows = []
    for (item, day), row in sorted(per_day.items()):
        if row["us_units"] or row["opp_units"]:
            row = dict(item=item, day=day, **row, us_avg_price=avg([row["us_units"], row["us_revenue"]]),
                       opp_avg_price=avg([row["opp_units"], row["opp_revenue"]]))
            day_rows.append(row)
    output = {"losses": len(games), "method": "official replay_mine _commit_unit hooks; actual realised SELL units and prices",
              "crop": crop, "crop_day": day_rows, "opponents": opponent_summary,
              "episodes": sorted(details, key=lambda x: x["episode"])}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"losses": len(games), "crop": crop}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
