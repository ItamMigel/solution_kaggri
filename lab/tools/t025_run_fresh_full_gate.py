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
    if not source.is_file() or not CONTROL.is_file() or any(not p.is_file() for p in OPPONENTS.values()):
        raise RuntimeError("a frozen input is missing")
    out = RUNS / f"t025_cma4_{tag[-4:]}_fresh_full_gate"
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
              "retro": retro, "candidate": str(source), "control": str(CONTROL),
              "candidate_sha256": sha(source), "control_sha256": sha(CONTROL),
              "opponents": {name: {"path": str(path), "sha256": sha(path)} for name, path in OPPONENTS.items()},
              "workers": 4, "expected_games": 640}
    (out / "selection.json").write_text(json.dumps(frozen, indent=2) + "\n")
    command = ["/workspace/solution_kaggri/.venv/bin/python", str(ROOT / "compare.py"),
               "--agent", f"{tag}={source}", "--agent", f"es5_c3g15={CONTROL}", "--baselines"]
    for name, path in OPPONENTS.items():
        command += ["--opponent", f"{name}={path}"]
    command += ["--seeds", *(str(seed) for seed in seeds), "--workers", "4", "--out", str(out / "arena"),
                "--decision-note", "T025 predeclared 16-world fresh full-core plus Horizon-family promotion gate; PASS requires joint one-sided paired lower >0 and no named opponent point estimate below -10pp."]
    subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run(["/workspace/solution_kaggri/.venv/bin/python", str(ROOT / "lab/tools/t025_fresh_full_panel_report.py"),
                    "--games", str(out / "arena/games.jsonl"), "--candidate", tag,
                    "--control", "es5_c3g15", "--out", str(out / "gate_report.json")], cwd=ROOT, check=True)
    result = json.loads((out / "gate_report.json").read_text())
    summary = json.loads((out / "arena/summary.json").read_text())
    result["compare_evaluation_valid"] = summary.get("evaluation_valid")
    result["source_hash_unchanged"] = sha(source) == frozen["candidate_sha256"]
    result["control_hash_unchanged"] = sha(CONTROL) == frozen["control_sha256"]
    result["passes_gate"] = bool(result["passes_gate"] and result["compare_evaluation_valid"]
                                 and result["source_hash_unchanged"] and result["control_hash_unchanged"])
    (out / "gate_report.json").write_text(json.dumps(result, indent=2) + "\n")
    if result["passes_gate"]:
        target = SHARED / f"candidates_wip/es6_{tag}_fullpanel"
        if target.exists():
            raise RuntimeError(f"refusing to overwrite candidate {target}")
        target.mkdir()
        shutil.copy2(source, target / "main.py")
        for name in ("selection.json", "seeds.json", "gate_report.json"):
            shutil.copy2(out / name, target / name)
        shutil.copy2(out / "arena/manifest.json", target / "arena_manifest.json")
        (target / "sha256.txt").write_text(f"{sha(source)}  main.py\n")
    verdict = "PASS" if result["passes_gate"] else "FAIL"
    message = (f"T025 fresh full-panel {verdict}: selected {tag}; paired={result['point_score_gain']*100:+.3f}pp, "
               f"one-sided lower={result['score_one_sided_lower_95']*100:+.3f}pp; "
               f"no-opponent-floor={result['passes_no_opponent_below_minus_10pp']}; evidence {out}")
    if result["passes_gate"]:
        message += f"; frozen {target} sha={sha(source)}"
    subprocess.run([str(SHARED / "bin/say"), "claude", message], check=True)
    print(message)


if __name__ == "__main__":
    main()
