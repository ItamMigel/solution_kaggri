#!/usr/bin/env python3
"""T043 read-only ladder report: positions, outcomes and own WHEAT trades."""
from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import io
import json
import multiprocessing as mp
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

TEAM = "misis biznessmenlb"
START = "2026-09-26T22:00:00"


def replay(path):
    with gzip.open(path, "rt") as f:
        return json.load(f)


def positions(farm):
    return (tuple(farm["farmer"]), *(tuple(x) for x in farm["hands"]))


def record(path, ratings):
    d = replay(path)
    names, rewards = d["info"]["TeamNames"], d["rewards"]
    us = names.index(TEAM)
    opponent = names[1-us]
    observed = []
    for state in d["steps"]:
        obs = state[0].get("observation") or {}
        if 9 <= obs.get("day", -1) <= 29:
            farms = obs["farms"]
            observed.append(positions(farms[us]) == positions(farms[1-us]))
    share = sum(observed) / len(observed) if observed else 0.0
    margin = rewards[us] - rewards[1-us]
    return {
        "path": str(path), "episode": d["info"]["EpisodeId"], "end": None,
        "opponent": opponent, "opponent_rating": ratings.get(opponent),
        "margin": margin, "outcome": "W" if margin > 0 else "L" if margin < 0 else "D",
        "position_match_share": share, "position_turns": len(observed),
        "class": "tape-clone" if share >= .5 else "reactive",
    }


def own_wheat(row):
    # t031 records accepted official-engine commits for both sides.  Its normal
    # report calls the non-team side "opponent"; flip us here to focus on ours.
    g = T031.mine((row["path"], row["us"], row["episode"], row["opponent"]))
    g["us"] = 1 - g["us"]
    s = T031.game_summary(g)
    return {
        "episode": row["episode"],
        "buy_units": s["opp_buy_units"], "buy_cost": s["opp_buy_cost"],
        "sell_units": s["opp_sell_units"], "sell_revenue": s["opp_sell_revenue"],
        "net_cashflow": s["cashflow_wheat"],
        "buy_mean_day": s["buy_mean_day"], "sell_mean_day": s["sell_mean_day"],
    }


def wdl(rows):
    return {x: sum(r["outcome"] == x for r in rows) for x in ("W", "D", "L")}


def avg(rows, key):
    return sum(r[key] for r in rows) / len(rows) if rows else None


def aggregate(rows, wheat):
    by_ep = {x["episode"]: x for x in wheat}
    ans = {}
    for key, subset in {"all": rows, **{c: [r for r in rows if r["class"] == c]
                                      for c in ("tape-clone", "reactive")}}.items():
        ws = [by_ep[x["episode"]] for x in subset]
        ans[key] = {
            "n": len(subset), "wdl": wdl(subset), "mean_margin": avg(subset, "margin"),
            "mean_opponent_rating_known": avg([x for x in subset if x["opponent_rating"] is not None], "opponent_rating"),
            "wheat_per_game": {k: avg(ws, k) for k in ("buy_units", "buy_cost", "sell_units", "sell_revenue", "net_cashflow")},
        }
    return ans


def time_bucket(rows):
    buckets = defaultdict(list)
    for r in rows:
        dt = datetime.fromisoformat(r["end"].replace("Z", "+00:00"))
        hour = dt.hour - dt.hour % 2
        stamp = dt.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat()
        buckets[stamp].append(r)
    return [{"start": k, "n": len(v), "wdl": wdl(v), "mean_margin": avg(v, "margin")}
            for k, v in sorted(buckets.items())]


def rating_buckets(rows):
    cuts = (("unknown", None, None), ("<2000", None, 2000), ("2000-2499", 2000, 2500),
            ("2500-2799", 2500, 2800), ("2800+", 2800, None))
    out = []
    for name, lo, hi in cuts:
        xs = [r for r in rows if (r["opponent_rating"] is None if name == "unknown" else
              r["opponent_rating"] is not None and (lo is None or r["opponent_rating"] >= lo) and (hi is None or r["opponent_rating"] < hi))]
        if xs:
            out.append({"rating_band": name, "n": len(xs), "wdl": wdl(xs), "mean_margin": avg(xs, "margin"),
                        "classes": {c: len([x for x in xs if x["class"] == c]) for c in ("tape-clone", "reactive")}})
    return out


def md(data):
    lines = ["# T043 — ladder continuation (read-only)", "",
             "Position class: d9–29 farmer+hands positions equal on ≥50% of observed turns = tape-clone.", ""]
    for sub, x in data["submissions"].items():
        a = x["aggregate"]
        lines += [f"## {sub}", "", "| class | n | W-D-L | mean margin | mean current opponent rating | WHEAT buy / sell / net cash per game |",
                  "|---|---:|---:|---:|---:|---:|"]
        for c in ("all", "tape-clone", "reactive"):
            z, q = a[c], a[c]["wheat_per_game"]
            rating = z["mean_opponent_rating_known"]
            rating_text = f"{rating:.0f}" if rating is not None else "n/a"
            lines.append(f"| {c} | {z['n']} | {z['wdl']['W']}-{z['wdl']['D']}-{z['wdl']['L']} | ${z['mean_margin']:+,.0f} | {rating_text} | {q['buy_units']:.1f}/${q['buy_cost']:,.0f} / {q['sell_units']:.1f}/${q['sell_revenue']:,.0f} / ${q['net_cashflow']:+,.0f} |")
        lines += ["", "2-hour outcome buckets:", "", "| start UTC | n | W-D-L | mean margin |", "|---|---:|---:|---:|"]
        lines += [f"| {b['start']} | {b['n']} | {b['wdl']['W']}-{b['wdl']['D']}-{b['wdl']['L']} | ${b['mean_margin']:+,.0f} |" for b in x["time_buckets"]]
        lines += ["", "Opponent current-rating × class:", "", "| rating | n | W-D-L | mean margin | clones / reactive |", "|---|---:|---:|---:|---:|"]
        lines += [f"| {b['rating_band']} | {b['n']} | {b['wdl']['W']}-{b['wdl']['D']}-{b['wdl']['L']} | ${b['mean_margin']:+,.0f} | {b['classes']['tape-clone']} / {b['classes']['reactive']} |" for b in x["rating_buckets"]]
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--es7", required=True); ap.add_argument("--es6", required=True)
    ap.add_argument("--episodes7", required=True); ap.add_argument("--episodes6", required=True)
    ap.add_argument("--leaderboard", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if not 1 <= a.workers <= 8: ap.error("workers must be 1..8")
    with zipfile.ZipFile(a.leaderboard) as z:
        name = z.namelist()[0]
        ratings = {r["TeamName"]: float(r["Score"]) for r in csv.DictReader(io.TextIOWrapper(z.open(name), "utf-8-sig")) if r.get("Score")}
    subs = {"es7_wm": (Path(a.es7), a.episodes7), "es6_c4g15": (Path(a.es6), a.episodes6)}
    out = {"task": "T043", "start": START, "generated_at": datetime.now(timezone.utc).isoformat(), "submissions": {}}
    all_wheat_rows = []
    for name, (root, episode_file) in subs.items():
        metadata = {x["id"]: x for x in json.JSONDecoder().raw_decode(Path(episode_file).read_text().lstrip())[0] if x["endTime"] >= START}
        rows = []
        for p in sorted(root.glob("episode-*-replay.json.gz")):
            r = record(p, ratings)
            if r["episode"] not in metadata: continue
            r["end"] = metadata[r["episode"]]["endTime"]
            d = replay(p); r["us"] = d["info"]["TeamNames"].index(TEAM)
            rows.append(r)
        if len(rows) != len(metadata): raise RuntimeError(f"{name}: {len(rows)} replays for {len(metadata)} episodes")
        with mp.Pool(a.workers) as pool:
            wheat = list(pool.imap_unordered(own_wheat, rows))
        all_wheat_rows.extend(wheat)
        out["submissions"][name] = {"episodes": rows, "wheat": sorted(wheat, key=lambda x: x["episode"]),
                                    "aggregate": aggregate(rows, wheat), "time_buckets": time_bucket(rows),
                                    "rating_buckets": rating_buckets(rows)}
    dest = Path(a.out)
    if not dest.suffix:
        dest = dest.with_suffix(".json")
    if dest.exists() or dest.with_suffix(".md").exists(): raise FileExistsError(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    dest.with_suffix(".md").write_text(md(out) + "\n")
    print(dest.with_suffix(".md"))


if __name__ == "__main__":
    T031 = None
    spec = importlib.util.spec_from_file_location("t031", Path(__file__).with_name("t031_wheat_arbitrage.py"))
    T031 = importlib.util.module_from_spec(spec); spec.loader.exec_module(T031)
    main()
