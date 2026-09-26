#!/usr/bin/env python3
"""Official-engine audit of G2 identity and early-tomato route completion."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path):
    ns = {"__file__": str(path), "__name__": "__g2_audit_agent__"}
    exec(compile(path.read_text(), str(path), "exec"), ns)
    return ns


def tomatoes(obs: dict) -> int:
    farm = obs["farms"][int(obs["player"])]
    return sum(1 for row in farm["tiles"] for tile in row
               if isinstance(tile, dict) and tile.get("crop") == "TOMATO")


def run(base_path: Path, candidate_path: Path, seeds: list[int]) -> dict:
    from kaggle_environments import make
    rows = []
    for seed in seeds:
        candidate = load(candidate_path)
        parent = candidate["agent"]
        daily, harvest_days = [], []
        previous_inv = 0

        def audited(obs, cfg=None):
            nonlocal previous_inv
            day = int(obs["step"]) // 24
            inv = sum(int(item.get("TOMATO", 0)) for item in (obs.get("private") or {}).get("inventories", []))
            if inv > previous_inv:
                harvest_days.append(day)
            previous_inv = inv
            if int(obs["step"]) % 24 == 0:
                daily.append((day, tomatoes(obs)))
            return parent(obs, cfg)

        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.run([audited, str(base_path)])
        report = candidate.get("_G2_REPORT", {})
        rows.append({"seed": seed, "status": [state.status for state in env.state], "daily_tomatoes": daily,
                     "harvest_days": harvest_days, "report": report})
    ok = all(row["status"] == ["DONE", "DONE"] and row["report"].get("errors") == 0
             and any(n > 0 for _, n in row["daily_tomatoes"]) and any(day >= 8 for day in row["harvest_days"])
             for row in rows)
    return {"ok": ok, "worlds": rows}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    value = run(a.base.resolve(), a.candidate.resolve(), a.seeds)
    a.out.write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps({"ok": value["ok"]}))
    if not value["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
