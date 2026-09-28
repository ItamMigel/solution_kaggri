#!/usr/bin/env python3
"""Report the T025 gate statistic after extending its P+M panel to all eight opponents.

The original gate directory supplies parthenos/metav4.  ``--extra-games``
supplies the same two agents versus control plus yhay/t2945/ozer/yaxon/pilkwang
on exactly the same 24 worlds.  The statistic is paired candidate-minus-control
score, averaged by whole world with weights control=1, P=2, M=2, and each
remaining opponent=1.  This is a retrospective diagnostic only; it does not
alter a gate's already recorded decision.
"""
import argparse
import json
from pathlib import Path

import numpy as np

WEIGHTS = {
    "best": 1, "parthenos": 2, "metav4": 2,
    "yhay0913": 1, "t2945": 1, "ozer_v45": 1, "yaxon": 1, "pilkwang": 1,
}

def score(row):
    seat = row["seat"]
    margin = row["rewards"][seat] - row["rewards"][1 - seat]
    return 1.0 if margin > 0 else .5 if margin == 0 else 0.0

def load(paths, agents):
    out, ignored = {}, {}
    for path in paths:
        for line in Path(path).read_text().splitlines():
            row = json.loads(line)
            if row.get("error") or "rewards" not in row:
                raise RuntimeError(f"invalid game row in {path}: {row}")
            if row["candidate"] not in agents:
                raise RuntimeError(f"unexpected candidate in {path}: {row['candidate']}")
            # compare.py supplies legacy baselines unless an explicit empty
            # --baselines terminator is present.  They are neither part of the
            # predeclared eight-unit panel nor a source of paired evidence, so
            # retain the planned games and make any extras auditable.
            if row["opponent"] not in WEIGHTS:
                ignored[row["opponent"]] = ignored.get(row["opponent"], 0) + 1
                continue
            key = (row["candidate"], row["opponent"], row["seed"], row["seat"])
            if key in out:
                raise RuntimeError(f"duplicate game: {key}")
            out[key] = (score(row), row["rewards"][row["seat"]] - row["rewards"][1 - row["seat"]])
    return out, ignored

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel-games", required=True, help="existing P+M games.jsonl")
    ap.add_argument("--extra-games", required=True, help="extension games.jsonl")
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--control", default="es5_c3g15")
    ap.add_argument("--out", required=True)
    ap.add_argument("--resamples", type=int, default=200000)
    ap.add_argument("--rng-seed", type=int, default=230923)
    a = ap.parse_args()
    rows, ignored = load([a.panel_games, a.extra_games], {a.candidate, a.control})
    seeds = sorted({key[2] for key in rows})
    world = []
    by_opponent = {}
    for seed in seeds:
        op_values = {}
        for opponent in WEIGHTS:
            paired = []
            for seat in (0, 1):
                kc = (a.candidate, opponent, seed, seat)
                kb = (a.control, opponent, seed, seat)
                if kc not in rows or kb not in rows:
                    raise RuntimeError(f"missing paired row for seed={seed}, opponent={opponent}, seat={seat}")
                sc, mc = rows[kc]; sb, mb = rows[kb]
                paired.append((sc - sb, mc - mb))
            op_values[opponent] = tuple(np.mean(paired, axis=0))
        ws = sum(WEIGHTS.values())
        world.append({"seed": seed,
                      "score": float(sum(WEIGHTS[o] * op_values[o][0] for o in WEIGHTS) / ws),
                      "cash": float(sum(WEIGHTS[o] * op_values[o][1] for o in WEIGHTS) / ws)})
        for opponent, value in op_values.items():
            by_opponent.setdefault(opponent, []).append(value)
    arr_score = np.array([x["score"] for x in world])
    arr_cash = np.array([x["cash"] for x in world])
    rng = np.random.default_rng(a.rng_seed)
    ix = rng.integers(0, len(world), size=(a.resamples, len(world)))
    bs_score = arr_score[ix].mean(axis=1)
    bs_cash = arr_cash[ix].mean(axis=1)
    result = {
        "worlds": len(world), "weights": WEIGHTS,
        "point_score_gain": float(arr_score.mean()), "cash_gain": float(arr_cash.mean()),
        "score_one_sided_lower_95": float(np.quantile(bs_score, .05)),
        "score_two_sided_95": [float(np.quantile(bs_score, .025)), float(np.quantile(bs_score, .975))],
        "cash_two_sided_95": [float(np.quantile(bs_cash, .025)), float(np.quantile(bs_cash, .975))],
        "passes_whole_panel_ni": bool(np.quantile(bs_score, .05) > -.020),
        "rng_seed": a.rng_seed, "resamples": a.resamples, "per_world": world,
        "ignored_unplanned_opponent_rows": ignored,
        "by_opponent": {o: {"score_gain": float(np.mean([v[0] for v in values])),
                              "cash_gain": float(np.mean([v[1] for v in values]))}
                        for o, values in by_opponent.items()},
    }
    Path(a.out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("worlds", "point_score_gain", "score_one_sided_lower_95", "cash_gain", "passes_whole_panel_ni")}))

if __name__ == "__main__":
    main()
