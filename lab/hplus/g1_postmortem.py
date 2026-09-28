#!/usr/bin/env python3
"""Read-only P&L decomposition of recorded G1 target-5 versus genome0 games.

Input is a ``compare.py --save-replays`` directory.  It replays every completed
game using the official replay miner, then pairs the candidate's own source
cash against genome0 by (world, opponent, seat).  This is diagnostic evidence,
not an evaluation or promotion runner.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab" / "tools"))
from replay_mine import mine  # noqa: E402


def cash_sources(record: dict, player: int) -> dict[str, float]:
    sells = record["sells"][player]
    buys = record["buys"][player]
    source = {f"sell:{item}": float(value[1]) for item, value in sells.items()}
    source.update({f"buy:{item}": -float(value[1]) for item, value in buys.items()})
    source["cost:hire"] = -float(record["hire_cost"][player])
    source["cost:land"] = -sum(float(item[2]) for item in record["land"][player])
    ops = record["unit_ops_ok"][player]
    for item in ("BUILD_COOP", "BUILD_PASTURE", "FEED", "CARE", "HARVEST", "PLANT", "WATER"):
        source[f"ok:{item}"] = float(ops.get(item, 0))
    source["final_cash"] = float(record["rewards"][player])
    # `money` is the post-step trajectory.  These snapshots distinguish a
    # durable production gain from an endgame-only liquidation effect.
    trajectory = record["money"][player]
    for day in (10, 17, 24, 28, 29):
        index = min(len(trajectory) - 1, (day + 1) * 24 - 1)
        source[f"cash_end_d{day}"] = float(trajectory[index])
    return source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in (args.run / "games.jsonl").read_text().splitlines()]
    mined: dict[tuple[int, str, int, str], list[dict[str, float]]] = {}
    for row in rows:
        if "error" in row or "replay_path" not in row:
            raise RuntimeError(f"incomplete replay row: {row}")
        player = int(row["seat"])
        record = mine(row["replay_path"], verbose=False)
        key = (int(row["seed"]), str(row["opponent"]), player, str(row["candidate"]))
        mined[key] = [cash_sources(record, 0), cash_sources(record, 1)]
    paired, opponent_paired = [], []
    aggregate: dict[str, list[float]] = defaultdict(list)
    opponent_aggregate: dict[str, list[float]] = defaultdict(list)
    for seed, opponent, seat, candidate in sorted(mined):
        if candidate != "g1_target5":
            continue
        base_all = mined[(seed, opponent, seat, "genome0")]
        trial_all = mined[(seed, opponent, seat, candidate)]
        base, trial = base_all[seat], trial_all[seat]
        delta = {name: trial.get(name, 0.0) - base.get(name, 0.0)
                 for name in sorted(set(base) | set(trial))}
        paired.append({"seed": seed, "opponent": opponent, "seat": seat, "delta": delta})
        for name, value in delta.items():
            aggregate[name].append(value)
        other = 1 - seat
        opponent_delta = {name: trial_all[other].get(name, 0.0) - base_all[other].get(name, 0.0)
                          for name in sorted(set(base_all[other]) | set(trial_all[other]))}
        opponent_paired.append({"seed": seed, "opponent": opponent, "seat": seat, "delta": opponent_delta})
        for name, value in opponent_delta.items():
            opponent_aggregate[name].append(value)
    summary = {name: {"mean": sum(values) / len(values), "values": values}
               for name, values in sorted(aggregate.items())}
    opponent_summary = {name: {"mean": sum(values) / len(values), "values": values}
                        for name, values in sorted(opponent_aggregate.items())}
    result = {"run": str(args.run.resolve()), "games": len(rows), "paired": paired, "mean_delta": summary,
              "opponent_paired": opponent_paired, "opponent_mean_delta": opponent_summary,
              "notes": ["Positive sell/cash deltas favour target5; negative buy/cost deltas favour target5.",
                        "Different candidate actions can change shared shop/market paths, so sources do not add exactly to final cash."]}
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    for name, value in summary.items():
        print(f"{name:20s} {value['mean']:+.1f}")


if __name__ == "__main__":
    main()
