#!/usr/bin/env python3
"""Fail-closed report for T025's predeclared fresh full-panel gate.

The 16 worlds are the resampling blocks.  Each block contains the same named
opponents in both seats, so every bootstrap draw retains cross-opponent world
correlation.  ``es1_g9`` and ``v5_market`` form one equal-weight family unit.
"""
import argparse
import json
from pathlib import Path

import numpy as np

CORE = ("mirror", "parthenos", "metav4", "yhay0913", "t2945", "ozer_v45", "yaxon", "pilkwang")
FAMILY = ("es1_g9", "v5_market")
ALL = CORE + FAMILY


def point(row):
    seat = row["seat"]
    margin = row["rewards"][seat] - row["rewards"][1 - seat]
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def load(path, agents, keep_agents):
    rows = {}
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        if (row.get("error") or row.get("status") != ["DONE", "DONE"]
                or row.get("invalid_steps") or "rewards" not in row):
            raise RuntimeError(f"invalid game row: {row}")
        if row["candidate"] not in agents or row["opponent"] not in ALL:
            raise RuntimeError(f"unexpected candidate/opponent: {row}")
        # A shared fresh-world run may contain a second predeclared candidate.
        # Validate every one of its rows above, but pair only the requested
        # candidate with the common frozen control below.
        if row["candidate"] not in keep_agents:
            continue
        key = (row["candidate"], row["opponent"], row["seed"], row["seat"])
        if key in rows:
            raise RuntimeError(f"duplicate paired row: {key}")
        rows[key] = (point(row), row["rewards"][row["seat"]] - row["rewards"][1 - row["seat"]])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--control", default="es5_c3g15")
    ap.add_argument("--allowed-agent", action="append", default=[],
                    help="additional candidate label whose rows are validated but excluded from this pair")
    ap.add_argument("--out", required=True)
    ap.add_argument("--resamples", type=int, default=200000)
    ap.add_argument("--rng-seed", type=int, default=230923)
    a = ap.parse_args()
    allowed = {a.candidate, a.control, *a.allowed_agent}
    rows = load(a.games, allowed, {a.candidate, a.control})
    seeds = sorted({key[2] for key in rows})
    per_world, by_opponent = [], {op: [] for op in ALL}
    for seed in seeds:
        per_op = {}
        for opponent in ALL:
            values = []
            for seat in (0, 1):
                kc = (a.candidate, opponent, seed, seat)
                kb = (a.control, opponent, seed, seat)
                if kc not in rows or kb not in rows:
                    raise RuntimeError(f"missing paired row: seed={seed}, opponent={opponent}, seat={seat}")
                values.append((rows[kc][0] - rows[kb][0], rows[kc][1] - rows[kb][1]))
            per_op[opponent] = np.mean(values, axis=0)
            by_opponent[opponent].append(per_op[opponent])
        strata = [per_op[op] for op in CORE] + [np.mean([per_op[op] for op in FAMILY], axis=0)]
        per_world.append({"seed": seed, "score": float(np.mean([x[0] for x in strata])),
                          "cash": float(np.mean([x[1] for x in strata]))})
    expected = len(seeds) * len(ALL) * 2 * 2
    if len(rows) != expected:
        raise RuntimeError(f"wrong game count: got {len(rows)}, expected {expected}")
    score = np.array([row["score"] for row in per_world])
    cash = np.array([row["cash"] for row in per_world])
    rng = np.random.default_rng(a.rng_seed)
    ix = rng.integers(0, len(seeds), size=(a.resamples, len(seeds)))
    boot = score[ix].mean(axis=1)
    result = {
        "worlds": len(seeds), "expected_valid_games": expected, "valid_games": len(rows),
        "core_strata": list(CORE), "family_stratum": list(FAMILY), "equal_weight_strata": len(CORE) + 1,
        "point_score_gain": float(score.mean()), "cash_gain": float(cash.mean()),
        "score_one_sided_lower_95": float(np.quantile(boot, .05)),
        "score_two_sided_95": [float(np.quantile(boot, .025)), float(np.quantile(boot, .975))],
        "cash_two_sided_95": [float(np.quantile(cash[ix].mean(axis=1), .025)), float(np.quantile(cash[ix].mean(axis=1), .975))],
        "by_opponent": {op: {"score_gain": float(np.mean(values, axis=0)[0]),
                               "cash_gain": float(np.mean(values, axis=0)[1])}
                        for op, values in by_opponent.items()},
        "per_world": per_world, "resamples": a.resamples, "rng_seed": a.rng_seed,
    }
    result["passes_lower_gt_zero"] = result["score_one_sided_lower_95"] > 0
    result["passes_no_opponent_below_minus_10pp"] = all(
        value["score_gain"] >= -.10 for value in result["by_opponent"].values())
    result["passes_gate"] = result["passes_lower_gt_zero"] and result["passes_no_opponent_below_minus_10pp"]
    Path(a.out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("worlds", "valid_games", "point_score_gain", "score_one_sided_lower_95", "passes_lower_gt_zero", "passes_no_opponent_below_minus_10pp", "passes_gate")}))


if __name__ == "__main__":
    main()
