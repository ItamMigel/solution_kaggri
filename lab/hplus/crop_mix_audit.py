#!/usr/bin/env python3
"""Official-engine T039 crop_mix identity and service audit; never submits."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    ns = {"__file__": str(path), "__name__": f"crop_mix_{path.stem}"}
    exec(compile(path.read_text(), str(path), "exec"), ns)
    return ns


def run(base_path: Path, candidate_path: Path, opponent: Path, seeds: list[int], *, identity: bool) -> list[dict]:
    from kaggle_environments import make

    rows = []
    for seed in seeds:
        base, candidate = load(base_path), load(candidate_path)
        diffs: list[int] = []

        def audited(obs, cfg=None):
            left, right = base["agent"](obs, cfg), candidate["agent"](obs, cfg)
            if json.dumps(left, sort_keys=True, separators=(",", ":")) != json.dumps(right, sort_keys=True, separators=(",", ":")):
                diffs.append(int(obs["step"]))
            return left if identity else right

        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.run([audited, str(opponent)])
        rows.append({"seed": seed, "status": [state.status for state in env.state], "diffs": diffs,
                     "stats": dict(candidate.get("_CM_STATS", {})), "reward": [state.reward for state in env.state]})
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True); p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--opponent", type=Path, required=True); p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--enabled", action="store_true"); p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    rows = run(a.base.resolve(), a.candidate.resolve(), a.opponent.resolve(), a.seeds, identity=not a.enabled)
    valid = all(row["status"] == ["DONE", "DONE"] for row in rows)
    action_identical = not any(row["diffs"] for row in rows)
    service_ok = all(not row["stats"].get("missed_service", 0) and not row["stats"].get("tile_mismatches", 0)
                     and not row["stats"].get("errors", 0) for row in rows)
    result = {"mode": "enabled" if a.enabled else "identity", "valid": valid,
              "action_identical": action_identical, "service_ok": service_ok, "rows": rows}
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("mode", "valid", "action_identical", "service_ok")}))
    if not valid or (not a.enabled and not action_identical) or (a.enabled and not service_ok):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
