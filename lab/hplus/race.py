"""Frozen-fold, paired Horizon+ capability and racing harness.

This is a thin, reproducible front-end to the official local ``compare.py``.
It never submits to Kaggle and never promotes automatically.  Genome zero must be
the first agent; every candidate is played on the same worlds, opponents and seats,
so ``summary.json`` contains paired deltas against it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import random
import subprocess
import sys
from datetime import datetime, timezone


ROOT = pathlib.Path("/workspace/solution_kaggri")
PYTHON = ROOT / ".venv/bin/python"
COMPARE_ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPARE = COMPARE_ROOT / "compare.py"
G9 = pathlib.Path("/workspace/shared/candidates/es1_g9/pkg/main.py")
V5 = ROOT / "agents/horizon_v5_market.py"
STAGES = {
    "capability": {"worlds": 2, "opponents": 2, "description": "2 worlds × g9 + one hard opponent × both seats"},
    "race": {"worlds": 4, "opponents": 3, "description": "4 worlds × g9 + v5 + one hard opponent × both seats"},
    "final": {"worlds": 8, "opponents": 5, "description": "8 worlds × g9 + v5 + three hard opponents × both seats"},
}


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_named(values: list[str]) -> dict[str, pathlib.Path]:
    result: dict[str, pathlib.Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected NAME=PATH, got {value!r}")
        name, raw = value.split("=", 1)
        path = pathlib.Path(raw).expanduser().resolve()
        if not name or name in result or not path.is_file():
            raise ValueError(f"invalid or duplicate agent {value!r}")
        result[name] = path
    return result


def _seeds(path: pathlib.Path) -> set[int]:
    value = json.loads(path.read_text())
    return set(value["seeds"] if isinstance(value, dict) else value)


def locked_fold(path: pathlib.Path, *, name: str, worlds: int, salt: int, excluded: set[int]) -> list[int]:
    """Create once or verify an immutable seed fold; exclusion prevents overlap."""
    if path.exists():
        saved = json.loads(path.read_text())
        if saved.get("name") != name or saved.get("worlds") != worlds or saved.get("salt") != salt:
            raise ValueError(f"locked fold parameters differ: {path}")
        seeds = saved["seeds"]
        if len(seeds) != worlds or len(set(seeds)) != worlds or set(seeds) & excluded:
            raise ValueError(f"locked fold is invalid or overlaps excluded seeds: {path}")
        return seeds
    rng = random.Random(salt)
    seeds: list[int] = []
    while len(seeds) < worlds:
        seed = rng.randrange(1, 2**31 - 1)
        if seed not in excluded and seed not in seeds:
            seeds.append(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": name, "worlds": worlds, "salt": salt, "seeds": seeds}, indent=2) + "\n")
    return seeds


def _paired_markdown(summary: dict, baseline: str) -> str:
    pairs = summary.get("pairwise", {}).get(baseline, {})
    lines = ["| Candidate | Paired score Δ | 95% CI | Paired margin Δ | 95% CI |", "|---|---:|---:|---:|---:|"]
    for name, value in pairs.items():
        if name == baseline:
            continue
        score_ci = value["paired_score_gain_95"]
        margin_ci = value["paired_margin_gain_95"]
        lines.append("| %s | %+.4f | [%+.4f, %+.4f] | %+.1f | [%+.1f, %+.1f] |" % (
            name, value["paired_score_gain"], score_ci[0], score_ci[1],
            value["paired_margin_gain"], margin_ci[0], margin_ci[1]))
    return "\n".join(lines)


def run(args: argparse.Namespace) -> None:
    stage = STAGES[args.stage]
    agents = parse_named(args.agent)
    if not agents or next(iter(agents)) != "genome0":
        raise ValueError("the first --agent must be genome0=... for paired deltas")
    if len(agents) > args.max_candidates:
        raise ValueError(f"stage permits at most {args.max_candidates} candidates including genome0")
    opponents = parse_named(args.opponent)
    if len(opponents) != stage["opponents"]:
        raise ValueError(f"{args.stage} requires exactly {stage['opponents']} opponents; got {len(opponents)}")
    if args.workers < 1 or args.workers > 22:
        raise ValueError("workers must be in [1, 22]")
    out = pathlib.Path(args.out).resolve()
    if out.exists():
        raise FileExistsError(f"refuse to overwrite {out}")

    excluded: set[int] = set()
    for item in args.exclude_seeds_file:
        excluded |= _seeds(pathlib.Path(item))
    fold = locked_fold(pathlib.Path(args.fold).resolve(), name=args.stage, worlds=stage["worlds"], salt=args.fold_salt, excluded=excluded)
    # Refuse accidental reuse of one named stage fold for another stage.
    if set(fold) & excluded:
        raise ValueError("fold overlaps excluded seeds")
    out.mkdir(parents=True)
    plan = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "stage": args.stage,
        "stage_contract": stage,
        "fold": str(pathlib.Path(args.fold).resolve()),
        "seeds": fold,
        "agents": {name: {"path": str(path), "sha256": _sha(path)} for name, path in agents.items()},
        "opponents": {name: {"path": str(path), "sha256": _sha(path)} for name, path in opponents.items()},
        "expected_games": len(agents) * len(opponents) * len(fold) * 2,
        "decision": "Paired delta vs genome0 only. No automatic selection or promotion.",
    }
    (out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    command = [str(PYTHON), str(COMPARE)]
    for name, path in agents.items():
        command += ["--agent", f"{name}={path}"]
    # The explicit empty option is intentional: every stage declares its full
    # opponent panel (including v5 when required), rather than inheriting the
    # compare.py default panel.
    command += ["--baselines"]
    for name, path in opponents.items():
        command += ["--opponent", f"{name}={path}"]
    command += ["--seeds", *map(str, fold), "--workers", str(args.workers), "--out", str(out / "compare")]
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    with (out / "command.txt").open("x") as log:
        log.write(" ".join(command) + "\n")
    proc = subprocess.run(command, cwd=COMPARE_ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (out / "compare.log").write_text(proc.stdout)
    if proc.returncode:
        raise RuntimeError(f"compare.py failed ({proc.returncode}); see {out/'compare.log'}")
    summary = json.loads((out / "compare" / "summary.json").read_text())
    (out / "PAIRED.md").write_text(
        "# Paired deltas against genome0\n\n" + _paired_markdown(summary, "genome0") + "\n\n"
        "This is a screening result, not a promotion decision.\n")
    print(out / "PAIRED.md")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=STAGES, required=True)
    parser.add_argument("--agent", action="append", default=[], required=True)
    parser.add_argument("--opponent", action="append", default=[], required=True)
    parser.add_argument("--fold", required=True)
    parser.add_argument("--fold-salt", type=int, required=True)
    parser.add_argument("--exclude-seeds-file", action="append", default=[])
    parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--max-candidates", type=int, default=24)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
