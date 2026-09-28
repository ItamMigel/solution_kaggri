#!/usr/bin/env python3
"""Execute the already-predeclared T025 fresh full-panel gate once g10 exists."""
import hashlib
import json
import secrets
import shutil
import subprocess
from pathlib import Path

ROOT = Path("/workspace/wt/codex")
SHARED = Path("/workspace/shared")
RUNS = SHARED / "runs"
RETRO = RUNS / "t025_cma4_whole_panel_retrospective"
CONTROL = SHARED / "candidates/es5_c3g15/pkg/main.py"
CHOICES = {
    "cma4_g005": RUNS / "cma4/gen_005/c/main.py",
    "cma4_g010": RUNS / "cma4/gen_010/c/main.py",
}
ADDITIONAL = {"cma4_g015": RUNS / "cma4/gen_015/c/main.py"}
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
    """Conservatively recover world seeds from manifest and explicit seed files."""
    out = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "seed" and type(value) is int and 0 <= value < 2**31:
                out.add(value)
            elif key == "seeds" and isinstance(value, list):
                out.update(v for v in value if type(v) is int and 0 <= v < 2**31)
            else:
                out |= values(value)
    elif isinstance(node, list):
        for value in node:
            out |= values(value)
    return out


def prior_seeds():
    files = set(RUNS.rglob("manifest.json")) | set(RUNS.rglob("*seeds*.json"))
    out = set()
    for path in sorted(files):
        try:
            out |= values(json.loads(path.read_text()))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RuntimeError(f"unreadable seed artifact: {path}")
    return out, sorted(str(p) for p in files)


def select():
    reports = {tag: json.loads((RETRO / f"{tag}_whole_panel_analysis.json").read_text()) for tag in CHOICES}
    # Larger lower bound, then point estimate, then g10 as declared in T025.
    tag = max(reports, key=lambda key: (reports[key]["score_one_sided_lower_95"],
                                        reports[key]["point_score_gain"], key == "cma4_g010"))
    return tag, reports


def main():
    tag, retro = select()
    source = CHOICES[tag]
    tested = {tag: source, **ADDITIONAL}
    if (not CONTROL.is_file() or any(not p.is_file() for p in tested.values())
            or any(not p.is_file() for p in OPPONENTS.values())):
        raise RuntimeError("a frozen input is missing")
    out = RUNS / f"t025_cma4_{tag[-4:]}_and_g015_fresh_full_gate"
    if out.exists():
        raise RuntimeError(f"refusing to overwrite {out}")
    excluded, artifacts = prior_seeds()
    seeds = []
    while len(seeds) < 16:
        value = secrets.randbelow(2**31)
        if value not in excluded and value not in seeds:
            seeds.append(value)
    out.mkdir(parents=True)
    (out / "seeds.json").write_text(json.dumps({"seeds": seeds, "excluded_seed_count": len(excluded),
        "seed_artifacts": artifacts}, indent=2) + "\n")
    frozen = {"selected": tag, "selection_rule": "larger retro lower; then point; then gen10",
              "retro": retro, "candidates": {name: {"path": str(path), "sha256": sha(path)}
                                                for name, path in tested.items()},
              "control": str(CONTROL), "control_sha256": sha(CONTROL),
              "opponents": {name: {"path": str(path), "sha256": sha(path)} for name, path in OPPONENTS.items()},
              "workers": 4, "expected_total_games": 960,
              "expected_pair_games_per_candidate": 640,
              "multiplicity": {"predeclared_candidates": list(tested), "tests": 2,
                               "note": "The selected g5/g10 centre and g15 are separately judged by the identical PASS rule on shared fresh worlds; no single-test interpretation."}}
    (out / "selection.json").write_text(json.dumps(frozen, indent=2) + "\n")
    command = ["/workspace/solution_kaggri/.venv/bin/python", str(ROOT / "compare.py")]
    for name, path in tested.items():
        command += ["--agent", f"{name}={path}"]
    command += ["--agent", f"es5_c3g15={CONTROL}", "--baselines"]
    for name, path in OPPONENTS.items():
        command += ["--opponent", f"{name}={path}"]
    command += ["--seeds", *(str(seed) for seed in seeds), "--workers", "4", "--out", str(out / "arena"),
                "--decision-note", "T025 predeclared 16-world fresh full-core plus Horizon-family promotion gate. Selected g5/g10 and additionally g15 are separately assessed by the identical PASS rule; two predeclared candidates, shared fresh worlds, multiplicity recorded. PASS requires joint one-sided paired lower >0 and no named opponent point estimate below -10pp."]
    subprocess.run(command, cwd=ROOT, check=True)
    summary = json.loads((out / "arena/summary.json").read_text())
    reports, messages = {}, []
    for name, path in tested.items():
        report_path = out / f"{name}_gate_report.json"
        report_command = ["/workspace/solution_kaggri/.venv/bin/python", str(ROOT / "lab/tools/t025_fresh_full_panel_report.py"),
                          "--games", str(out / "arena/games.jsonl"), "--candidate", name,
                          "--control", "es5_c3g15", "--out", str(report_path)]
        for allowed in tested:
            if allowed != name:
                report_command += ["--allowed-agent", allowed]
        subprocess.run(report_command, cwd=ROOT, check=True)
        result = json.loads(report_path.read_text())
        result["compare_evaluation_valid"] = summary.get("evaluation_valid")
        result["source_hash_unchanged"] = sha(path) == frozen["candidates"][name]["sha256"]
        result["control_hash_unchanged"] = sha(CONTROL) == frozen["control_sha256"]
        result["multiplicity"] = frozen["multiplicity"]
        result["passes_gate"] = bool(result["passes_gate"] and result["compare_evaluation_valid"]
                                     and result["source_hash_unchanged"] and result["control_hash_unchanged"])
        report_path.write_text(json.dumps(result, indent=2) + "\n")
        reports[name] = result
        if result["passes_gate"]:
            target = SHARED / f"candidates_wip/es6_{name}_fullpanel"
            if target.exists():
                raise RuntimeError(f"refusing to overwrite candidate {target}")
            target.mkdir()
            shutil.copy2(path, target / "main.py")
            for evidence in ("selection.json", "seeds.json", report_path.name):
                shutil.copy2(out / evidence, target / evidence)
            shutil.copy2(out / "arena/manifest.json", target / "arena_manifest.json")
            (target / "sha256.txt").write_text(f"{sha(path)}  main.py\n")
            messages.append(f"{name}=PASS paired={result['point_score_gain']*100:+.3f}pp lower={result['score_one_sided_lower_95']*100:+.3f}pp floor={result['passes_no_opponent_below_minus_10pp']}; wip={target}")
        else:
            messages.append(f"{name}=FAIL paired={result['point_score_gain']*100:+.3f}pp lower={result['score_one_sided_lower_95']*100:+.3f}pp floor={result['passes_no_opponent_below_minus_10pp']}")
    (out / "gate_reports.json").write_text(json.dumps({"multiplicity": frozen["multiplicity"], "reports": reports}, indent=2) + "\n")
    message = f"T025 fresh full-panel (two predeclared tests, shared worlds): {'; '.join(messages)}; evidence {out}"
    subprocess.run([str(SHARED / "bin/say"), "claude", message], check=True)
    print(message)


if __name__ == "__main__":
    main()
