#!/usr/bin/env python3
"""Run one declared T025 CMA4 full-panel gate against the current control.

The invocation is intentionally one generation at a time.  It refuses reused
output paths and recovers every prior recorded seed before drawing its panel.
This makes the companion resume loop safe to leave running between gates.
"""
import argparse
import hashlib
import json
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/workspace/wt/codex")
SHARED = Path("/workspace/shared")
RUNS = SHARED / "runs"
CONTROL = SHARED / "candidates/es7_wm/pkg/main.py"
CONTROL_NAME = "es7_wm"
WHEAT_GENES = {
    "wm_on": True, "wm_buy_day0": 6, "wm_buy_day1": 17, "wm_buy_price_max": 30,
    "wm_feed_floor": 20, "wm_buy_cap": 8, "wm_cash_reserve": 2000,
    "wm_sell_day0": 10, "wm_sell_day1": 28, "wm_sell_price_min": 40,
    "wm_sell_reserve": 35, "wm_sell_cap": 8,
}
OPPONENTS = {
    "mirror": CONTROL,
    "parthenos": SHARED / "opponents/pool/parthenos_robust/main.py",
    "metav4": SHARED / "opponents/pool/tschinkel_metav4_v13/main.py",
    "yhay0913": SHARED / "opponents/pool/yhay_router0913/main.py",
    "t2945": SHARED / "opponents/pool/tschinkel2945/main.py",
    "ozer_v45": SHARED / "opponents/pool/ozer_v45/main.py",
    "yaxon": SHARED / "opponents/pool/yaxon_reactive_v5/main.py",
    "pilkwang": SHARED / "opponents/pool/pilkwang_struct/main.py",
    "es1_g9": SHARED / "candidates/es1_g9/pkg/main.py",
    "v5_market": ROOT / "agents/horizon_v5_market.py",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def values(node):
    if isinstance(node, dict):
        out = set()
        for key, value in node.items():
            if key == "seed" and type(value) is int and 0 <= value < 2**31:
                out.add(value)
            elif key == "seeds" and isinstance(value, list):
                out.update(v for v in value if type(v) is int and 0 <= v < 2**31)
            else:
                out |= values(value)
        return out
    if isinstance(node, list):
        return set().union(*(values(value) for value in node)) if node else set()
    return set()


def prior_seeds():
    artifacts = sorted(set(RUNS.rglob("manifest.json")) | set(RUNS.rglob("*seeds*.json")))
    excluded = set()
    for path in artifacts:
        try:
            excluded |= values(json.loads(path.read_text()))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"unreadable seed artifact: {path}") from exc
    return excluded, [str(path) for path in artifacts]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", type=int, required=True, help="completed CMA generation label")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.gen < 0 or a.gen % 5:
        ap.error("--gen must be a non-negative multiple of five")
    if not 1 <= a.workers <= 4:
        ap.error("gate workers must be 1..4")
    raw_candidate = RUNS / f"cma4/gen_{a.gen:03d}/c/main.py"
    out = RUNS / f"t025_cma4_g{a.gen:03d}_full_panel_vs_es7"
    if out.exists():
        raise RuntimeError(f"refusing to overwrite {out}")
    inputs = [raw_candidate, CONTROL, *OPPONENTS.values()]
    if any(not path.is_file() for path in inputs):
        raise RuntimeError("missing frozen candidate, control, or opponent input")
    excluded, artifacts = prior_seeds()
    seeds = []
    while len(seeds) < 16:
        seed = secrets.randbelow(2**31)
        if seed not in excluded and seed not in seeds:
            seeds.append(seed)
    out.mkdir(parents=True)
    # The CMA objective predates the promoted market layer.  Every gate wraps
    # the immutable centre with the exact es7 WHEAT genes, freezes that file
    # beside the evidence, and compares the composed agent to es7_wm.
    sys.path.insert(0, str(ROOT))
    from lab.hplus.wheat_market import build as build_wheat_market
    candidate = out / "candidate_with_wheat" / "main.py"
    wheat_info = build_wheat_market(raw_candidate, WHEAT_GENES, candidate)
    (out / "seeds.json").write_text(json.dumps({"seeds": seeds,
        "excluded_seed_count": len(excluded), "seed_artifacts": artifacts}, indent=2) + "\n")
    frozen = {"generation": a.gen,
              "raw_cma_candidate": {"path": str(raw_candidate), "sha256": sha(raw_candidate)},
              "candidate": {"path": str(candidate), "sha256": sha(candidate), "wheat_market": wheat_info},
              "control": {"path": str(CONTROL), "sha256": sha(CONTROL)},
              "opponents": {name: {"path": str(path), "sha256": sha(path)} for name, path in OPPONENTS.items()},
              "workers": a.workers, "expected_games": 640,
              "criterion": "9 equal-weight strata; joint 16-world bootstrap lower > 0; no named opponent below -10pp"}
    (out / "frozen_inputs.json").write_text(json.dumps(frozen, indent=2) + "\n")
    candidate_name, control_name = f"cma4_g{a.gen:03d}_wm", CONTROL_NAME
    command = ["/workspace/solution_kaggri/.venv/bin/python", str(ROOT / "compare.py"),
               "--agent", f"{candidate_name}={candidate}", "--agent", f"{control_name}={CONTROL}", "--baselines"]
    for name, path in OPPONENTS.items():
        command += ["--opponent", f"{name}={path}"]
    command += ["--seeds", *(str(seed) for seed in seeds), "--workers", str(a.workers),
                "--out", str(out / "arena"), "--decision-note",
                "T025 periodic fresh full-panel gate: CMA centre plus frozen es7 WHEAT layer against promoted es7_wm; no Kaggle submission."]
    subprocess.run(command, cwd=ROOT, check=True)
    report = out / "gate_report.json"
    subprocess.run(["/workspace/solution_kaggri/.venv/bin/python", str(ROOT / "lab/tools/t025_fresh_full_panel_report.py"),
                    "--games", str(out / "arena/games.jsonl"), "--candidate", candidate_name,
                    "--control", control_name, "--out", str(report)], cwd=ROOT, check=True)
    result = json.loads(report.read_text())
    summary = json.loads((out / "arena/summary.json").read_text())
    result["compare_evaluation_valid"] = summary.get("evaluation_valid")
    result["raw_cma_hash_unchanged"] = sha(raw_candidate) == frozen["raw_cma_candidate"]["sha256"]
    result["candidate_hash_unchanged"] = sha(candidate) == frozen["candidate"]["sha256"]
    result["control_hash_unchanged"] = sha(CONTROL) == frozen["control"]["sha256"]
    result["passes_gate"] = bool(result["passes_gate"] and result["compare_evaluation_valid"]
                                 and result["raw_cma_hash_unchanged"] and result["candidate_hash_unchanged"]
                                 and result["control_hash_unchanged"])
    report.write_text(json.dumps(result, indent=2) + "\n")
    wip = None
    if result["passes_gate"]:
        wip = SHARED / f"candidates_wip/es8_cma4_g{a.gen:03d}_fullpanel"
        if wip.exists():
            raise RuntimeError(f"refusing to overwrite candidate evidence {wip}")
        wip.mkdir()
        for path in (candidate, out / "seeds.json", out / "frozen_inputs.json", report, out / "arena/manifest.json"):
            shutil.copy2(path, wip / ("main.py" if path == candidate else path.name))
        (wip / "sha256.txt").write_text(f"{sha(candidate)}  main.py\n")
    message = (f"T025 CMA4 g{a.gen:03d}+WHEAT fresh full-panel vs es7_wm: "
               f"{'PASS' if result['passes_gate'] else 'FAIL'} paired={result['point_score_gain']*100:+.3f}pp "
               f"lower={result['score_one_sided_lower_95']*100:+.3f}pp; evidence={out}"
               + (f"; WIP={wip}" if wip else ""))
    subprocess.run([str(SHARED / "bin/say"), "claude", message], check=True)
    print(message)


if __name__ == "__main__":
    main()
