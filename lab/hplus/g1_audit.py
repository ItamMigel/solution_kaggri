#!/usr/bin/env python3
"""Official-engine audit for G1 identity and route completion; never submits."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path):
    ns = {"__file__": str(path), "__name__": "__g1_audit_agent__"}
    exec(compile(path.read_text(), str(path), "exec"), ns)
    return ns


def geese(obs: dict) -> int:
    farm = obs["farms"][int(obs["player"])]
    return sum(1 for row in farm["tiles"] for tile in row
               if isinstance(tile, dict) and tile.get("animal") == "GOOSE")


def run_identity(base_path: Path, default_path: Path, seeds: list[int]) -> dict:
    from kaggle_environments import make

    all_rows = []
    for seed in seeds:
        base, default = load(base_path), load(default_path)
        mismatches = []

        def audited(obs, cfg=None):
            left = base["agent"](obs, cfg)
            right = default["agent"](obs, cfg)
            if json.dumps(left, sort_keys=True, separators=(",", ":")) != json.dumps(right, sort_keys=True, separators=(",", ":")):
                mismatches.append(int(obs["step"]))
            return left

        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.run([audited, str(base_path)])
        all_rows.append({"seed": seed, "status": [state.status for state in env.state],
                         "calls": len(env.logs), "mismatch_steps": mismatches})
    ok = all(row["status"] == ["DONE", "DONE"] and not row["mismatch_steps"] for row in all_rows)
    return {"ok": ok, "worlds": all_rows}


def run_target(base_path: Path, candidate_path: Path, target: int, seeds: list[int]) -> dict:
    from kaggle_environments import make

    rows = []
    for seed in seeds:
        candidate = load(candidate_path)
        parent = candidate["agent"]
        by_day: list[tuple[int, int]] = []

        def audited(obs, cfg=None):
            if int(obs["step"]) % 24 == 0:
                by_day.append((int(obs["step"]) // 24, geese(obs)))
            return parent(obs, cfg)

        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.run([audited, str(base_path)])
        report = candidate.get("_G1_REPORT", {})
        final_geese = geese(env.state[0].observation)
        rows.append({"seed": seed, "status": [state.status for state in env.state],
                     "daily_geese": by_day, "final_geese": final_geese, "report": report})
    ok = all(row["status"] == ["DONE", "DONE"] and row["report"].get("mismatches") == 0
             and row["report"].get("errors") == 0 and row["report"].get("confirmed_sites") == target
             and row["final_geese"] == target for row in rows)
    return {"ok": ok, "target": target, "worlds": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--default", type=Path, required=True)
    parser.add_argument("--candidate", action="append", default=[], metavar="TARGET=PATH")
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base, default = args.base.resolve(), args.default.resolve()
    result = {"identity": run_identity(base, default, args.seeds), "targets": {}}
    for item in args.candidate:
        raw_target, raw_path = item.split("=", 1)
        target = int(raw_target)
        result["targets"][str(target)] = run_target(base, Path(raw_path).resolve(), target, args.seeds)
    result["ok"] = result["identity"]["ok"] and all(value["ok"] for value in result["targets"].values())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"ok": result["ok"], "identity": result["identity"]["ok"],
                      "targets": {key: value["ok"] for key, value in result["targets"].items()}}))
    if not result["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
