#!/usr/bin/env python3
"""Fresh T025-format full gate for T031's market-only es6 wrapper.

Never submits.  It is intentionally a one-shot evidence gate: a pass is only
a request for independent review, not a candidate creation or promotion.
"""
from __future__ import annotations

import argparse
import json
import secrets
import subprocess
from pathlib import Path

from t025_periodic_full_panel_gate import CONTROL, OPPONENTS, ROOT, RUNS, SHARED, prior_seeds, sha


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    candidate, out = args.candidate.resolve(), args.out.resolve()
    if not candidate.is_file() or out.exists():
        raise RuntimeError("candidate missing or output already exists")
    if not 1 <= args.workers <= 4:
        raise ValueError("workers must be 1..4")
    excluded, artifacts = prior_seeds()
    seeds: list[int] = []
    while len(seeds) < 16:
        seed = secrets.randbelow(2**31)
        if seed not in excluded and seed not in seeds:
            seeds.append(seed)
    out.mkdir(parents=True)
    frozen = {"candidate": {"path": str(candidate), "sha256": sha(candidate)},
              "control": {"path": str(CONTROL), "sha256": sha(CONTROL)},
              "opponents": {k: {"path": str(v), "sha256": sha(v)} for k, v in OPPONENTS.items()},
              "workers": args.workers, "expected_games": 640,
              "criterion": "T025 nine equal-weight strata; joint 16-world one-sided lower > 0; every named opponent >= -10pp"}
    (out / "seeds.json").write_text(json.dumps({"seeds": seeds, "excluded_seed_count": len(excluded), "seed_artifacts": artifacts}, indent=2) + "\n")
    (out / "frozen_inputs.json").write_text(json.dumps(frozen, indent=2) + "\n")
    command = ["/workspace/solution_kaggri/.venv/bin/python", str(ROOT / "compare.py"),
               "--agent", f"wheat_market={candidate}", "--agent", f"es6_c4g15={CONTROL}", "--baselines"]
    for name, path in OPPONENTS.items(): command += ["--opponent", f"{name}={path}"]
    command += ["--seeds", *(str(s) for s in seeds), "--workers", str(args.workers), "--out", str(out / "arena"),
                "--decision-note", "T031 market-only full gate; never a Kaggle submission."]
    subprocess.run(command, cwd=ROOT, check=True)
    report = out / "gate_report.json"
    subprocess.run(["/workspace/solution_kaggri/.venv/bin/python", str(ROOT / "lab/tools/t025_fresh_full_panel_report.py"),
                    "--games", str(out / "arena/games.jsonl"), "--candidate", "wheat_market", "--control", "es6_c4g15", "--out", str(report)], cwd=ROOT, check=True)
    result = json.loads(report.read_text())
    summary = json.loads((out / "arena/summary.json").read_text())
    result.update(compare_evaluation_valid=summary.get("evaluation_valid"),
                  candidate_hash_unchanged=sha(candidate) == frozen["candidate"]["sha256"],
                  control_hash_unchanged=sha(CONTROL) == frozen["control"]["sha256"])
    result["passes_gate"] = bool(result["passes_gate"] and result["compare_evaluation_valid"] and result["candidate_hash_unchanged"] and result["control_hash_unchanged"])
    report.write_text(json.dumps(result, indent=2) + "\n")
    msg = (f"T031 market-only full gate vs es6: {'PASS' if result['passes_gate'] else 'FAIL'} "
           f"paired={result['point_score_gain']*100:+.3f}pp lower={result['score_one_sided_lower_95']*100:+.3f}pp; evidence={out}; never submitted")
    subprocess.run([str(SHARED / "bin/say"), "claude", msg], check=True)
    print(msg)


if __name__ == "__main__": main()
