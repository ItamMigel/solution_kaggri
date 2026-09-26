#!/usr/bin/env python3
"""Official-engine identity/activation audit for T035; never submits."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    ns = {"__file__": str(path), "__name__": f"audit_{path.stem}"}
    exec(compile(path.read_text(), str(path), "exec"), ns)
    return ns


def identity(base_path: Path, candidate_path: Path, opponent: Path, seeds: list[int]) -> list[dict]:
    from kaggle_environments import make
    rows = []
    for seed in seeds:
        base, candidate = load(base_path), load(candidate_path); diffs = []
        def audited(obs, cfg=None):
            left, right = base["agent"](obs, cfg), candidate["agent"](obs, cfg)
            if json.dumps(left, sort_keys=True, separators=(",", ":")) != json.dumps(right, sort_keys=True, separators=(",", ":")):
                diffs.append(int(obs["step"]))
            return left
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.run([audited, str(opponent)])
        rows.append({"seed": seed, "status": [s.status for s in env.state], "diffs": diffs,
                     "report": dict(candidate.get("_RLN_REPORT", {}))})
    return rows


def activation(candidate_path: Path, opponent: Path, seeds: list[int]) -> list[dict]:
    from kaggle_environments import make
    rows = []
    for seed in seeds:
        candidate = load(candidate_path)
        env = make("kaggriculture", configuration={"seed": seed}, debug=False)
        env.run([candidate["agent"], str(opponent)])
        rows.append({"seed": seed, "status": [s.status for s in env.state],
                     "report": dict(candidate.get("_RLN_REPORT", {})), "rewards": [s.reward for s in env.state]})
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True); p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--mirror", type=Path, required=True); p.add_argument("--tape", action="append", required=True, metavar="NAME=PATH")
    p.add_argument("--reactive", action="append", required=True, metavar="NAME=PATH"); p.add_argument("--seeds", type=int, nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(); base, cand = a.base.resolve(), a.candidate.resolve()
    def named(value: str) -> tuple[str, Path]:
        name, raw = value.split("=", 1)
        if not name or not Path(raw).is_file(): raise ValueError(f"invalid NAME=PATH: {value}")
        return name, Path(raw).resolve()
    mirrors = identity(base, cand, a.mirror.resolve(), a.seeds)
    tapes = {name: identity(base, cand, path, a.seeds) for name, path in map(named, a.tape)}
    reactive = {name: activation(cand, path, a.seeds) for name, path in map(named, a.reactive)}
    done = lambda rows: all(row["status"] == ["DONE", "DONE"] for row in rows)
    identity_ok = done(mirrors) and not any(r["diffs"] for r in mirrors) and all(done(rows) and not any(r["diffs"] for r in rows) for rows in tapes.values())
    activation_ok = all(done(rows) and all(r["report"].get("nonclone", 0) >= 1 for r in rows) for rows in reactive.values())
    result = {"identity_ok": identity_ok, "activation_ok": activation_ok, "mirror": mirrors, "tapes": tapes, "reactive": reactive}
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"identity_ok": identity_ok, "activation_ok": activation_ok}))
    if not (identity_ok and activation_ok): raise SystemExit(2)


if __name__ == "__main__":
    main()
