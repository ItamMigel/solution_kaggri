#!/usr/bin/env python3
"""T030: replay-exact wheat production/feed attribution, never a counterfactual.

The 39 ladder losses and all 41 available wins are re-executed in the official
engine.  Every reported plant, harvest, buy and feed is a successful engine
action; daily hands/land/tile stock are end-of-day public state snapshots.
"""
from __future__ import annotations

import argparse
import glob
import json
import multiprocessing as mp
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replay_mine import mine  # noqa: E402

TEAM = "misis biznessmenlb"
EVENTS = ("wheat_tiles_planted", "wheat_tiles_harvested", "wheat_units_harvested",
          "buy_seed_wheat_units", "buy_seed_wheat_cost", "buy_product_wheat_units",
          "buy_product_wheat_cost", "feed_actions", "wheat_units_fed", "hands_hired")
STATE = ("wheat_tiles_eod", "quadrants_eod", "hands_eod")


def games(replays: str):
    rows = []
    for raw in sorted(glob.glob(str(Path(replays) / "episode-*-replay.json"))):
        replay = json.loads(Path(raw).read_text())
        teams, rewards = replay["info"]["TeamNames"], replay["rewards"]
        if TEAM not in teams:
            continue
        us = teams.index(TEAM)
        if rewards[us] == rewards[1 - us]:
            continue
        rows.append((raw, us, "loss" if rewards[us] < rewards[1 - us] else "win",
                     replay["info"]["EpisodeId"], teams[1-us]))
    return rows


def replay(row):
    raw, us, cohort, episode, opponent = row
    return {"us": us, "cohort": cohort, "episode": episode, "opponent": opponent,
            "result": mine(raw, verbose=False)}


def add(dst, source, day, keys):
    values = source.get(str(day), source.get(day, {}))
    for key in keys:
        dst[key] += values.get(key, 0)


def mean_day(totals, n):
    return {str(day): {key: totals[day][key] / n for key in (*EVENTS, *STATE)} for day in range(30)}


def total(values, keys):
    return {key: sum(values[str(day)][key] for day in range(30)) for key in keys}


def fmt_pair(row, key, precision=1):
    return f"{row['us'][key]:.{precision}f}/{row['opponent'][key]:.{precision}f}"


def markdown(result):
    lines = ["# T030 — откуда берётся лишняя пшеница соперника", "",
             "Повторное исполнение тех же 80 ladder-replay в official engine 1.32.7: 39 поражений и все 41 доступные победы. "
             "Посадки, harvest, покупки, FEED и HIRE — только успешные действия движка; земля и `P_WHEAT` — EOD-снимок. "
             "Это наблюдательная атрибуция, не причинный counterfactual.", ""]
    lines += ["| когорта | Δ opponent−us WHEAT sold | Δ planted tiles | Δ harvested units | Δ BUY_PRODUCT WHEAT $ | Δ FEED |",
              "|---|---:|---:|---:|---:|---:|"]
    for cohort in ("loss", "win"):
        s = result["summary"][cohort]
        lines.append("| %s (n=%d) | %+.1f | %+.1f | %+.1f | %s | %+.1f |" % (
            cohort, s["games"], s["opp_minus_us_wheat_sold"], s["opp_minus_us"]["wheat_tiles_planted"],
            s["opp_minus_us"]["wheat_units_harvested"],
            f"${s['opp_minus_us']['buy_product_wheat_cost']:+,.1f}", s["opp_minus_us"]["feed_actions"]))
    loss = result["summary"]["loss"]
    lines += ["", "В losses дополнительный проданный WHEAT соперника не возникает из большего собственного crop-производства: "
              f"у него {loss['opp_minus_us']['wheat_units_harvested']:+.1f} harvested units и "
              f"{loss['opp_minus_us']['wheat_tiles_planted']:+.1f} посадок относительно нас, но "
              f"{loss['opp_minus_us']['buy_product_wheat_units']:+.1f} купленных товарных WHEAT. "
              f"При всего {loss['opp_minus_us']['feed_actions']:+.1f} FEED это наблюдаемо согласуется с перепродажей/market turnover, а не с замещением покупного корма собственным урожаем. "
              f"Земля после d11 почти равна (~3.1–3.2 квадранта), seasonal HIRE лишь {loss['opp_minus_us']['hands_hired']:+.1f}; это не чистый land/labour дефицит."]
    lines += ["", "## По дням — losses (среднее на игру, us/opponent)", "",
              "| d | P_WHEAT EOD | plant tiles | harvest units | quadrants | hired hands | seed buy | product-WHEAT $ | FEED |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    rows = result["per_day"]["loss"]
    for day in range(30):
        r = rows[str(day)]
        lines.append("| %d | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            day, fmt_pair(r, "wheat_tiles_eod"), fmt_pair(r, "wheat_tiles_planted"),
            fmt_pair(r, "wheat_units_harvested"), fmt_pair(r, "quadrants_eod"), fmt_pair(r, "hands_hired"),
            fmt_pair(r, "buy_seed_wheat_units"), fmt_pair(r, "buy_product_wheat_cost"), fmt_pair(r, "feed_actions")))
    lines += ["", "## Контраст wins (агрегат на игру)", "",
              "| метрика | us | opponent | Δ opponent−us |",
              "|---|---:|---:|---:|"]
    for key in ("wheat_tiles_planted", "wheat_units_harvested", "buy_seed_wheat_units", "buy_seed_wheat_cost",
                "buy_product_wheat_units", "buy_product_wheat_cost", "feed_actions", "wheat_units_fed"):
        s = result["summary"]["win"]
        lines.append("| %s | %.1f | %.1f | %+.1f |" % (key, s["us"][key], s["opponent"][key], s["opp_minus_us"][key]))
    lines += ["", "Полный машиночитаемый разрез, включая оба игрока каждого дня: `runs/t030_wheat_sources_v2/wheat.json`."]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replays", default="/workspace/shared/replays/t028")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--render", action="store_true", help="render an existing JSON result without re-running replays")
    args = ap.parse_args()
    if not 1 <= args.workers <= 8:
        ap.error("workers must be 1..8")
    out = Path(args.out)
    if args.render:
        result = json.loads(out.read_text())
        out.with_suffix(".md").write_text(markdown(result))
        print(out.with_suffix(".md"))
        return
    rows = games(args.replays)
    count = {kind: sum(row[2] == kind for row in rows) for kind in ("loss", "win")}
    if count != {"loss": 39, "win": 41}:
        raise RuntimeError(f"expected 39 losses and 41 wins, got {count}")
    with mp.Pool(args.workers) as pool:
        mined = list(pool.imap_unordered(replay, rows))
    totals = {cohort: {role: [defaultdict(float) for _ in range(30)] for role in ("us", "opponent")}
              for cohort in ("loss", "win")}
    wheat_sold = {cohort: {role: 0.0 for role in ("us", "opponent")} for cohort in ("loss", "win")}
    for game in mined:
        cohort, us, result = game["cohort"], game["us"], game["result"]
        for pid, role in ((us, "us"), (1-us, "opponent")):
            for day in range(30):
                add(totals[cohort][role][day], result["wheat_daily"][pid], day, EVENTS)
                # Hands are deliberately fired at every day boundary; the
                # public EOD `hands` snapshot is therefore almost always 0.
                # Successful per-day HIRE calls are the meaningful labour
                # measure (and are action-hooked by replay_mine).
                totals[cohort][role][day]["hands_hired"] += result["hires"][pid].get(day, result["hires"][pid].get(str(day), 0))
                state = next((x for x in result["wheat_state"][pid] if x["day"] == day), {})
                for key in STATE:
                    totals[cohort][role][day][key] += state.get(key, 0)
            wheat_sold[cohort][role] += result["sells"][pid].get("WHEAT", [0, 0])[0]
    per_day, summary = {}, {}
    for cohort in ("loss", "win"):
        by_role = {role: mean_day(totals[cohort][role], count[cohort]) for role in ("us", "opponent")}
        per_day[cohort] = {str(day): {role: by_role[role][str(day)] for role in by_role} for day in range(30)}
        sums = {role: total(by_role[role], EVENTS) for role in by_role}
        summary[cohort] = {"games": count[cohort], "us": sums["us"], "opponent": sums["opponent"],
                           "opp_minus_us": {key: sums["opponent"][key] - sums["us"][key] for key in EVENTS},
                           "opp_minus_us_wheat_sold": (wheat_sold[cohort]["opponent"] - wheat_sold[cohort]["us"]) / count[cohort]}
    output = {"method": "official engine replay, successful action hooks; state is EOD", "cohort_counts": count,
              "summary": summary, "per_day": per_day,
              "episodes": sorted({g["cohort"]: [] for g in mined}.items())}
    # Preserve the episode identities without serialising the large raw miner output.
    output["episodes"] = sorted(
        ({"episode": g["episode"], "cohort": g["cohort"], "opponent": g["opponent"]} for g in mined),
        key=lambda x: x["episode"])
    out.parent.mkdir(parents=True, exist_ok=False)
    out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    report = out.with_suffix(".md")
    report.write_text(markdown(output))
    print(report)


if __name__ == "__main__":
    main()
