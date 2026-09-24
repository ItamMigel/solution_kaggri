#!/bin/bash
# usage: fetch_team.sh <team_id> <n_per_sub> <outdir>  — all active subs of one team
cd "$(dirname "$0")"; /workspace/solution_kaggri/.venv/bin/python - "$@" <<'PY'
import json, os, subprocess, sys
from fetch_top import run, jl
tid, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]; os.makedirs(out, exist_ok=True); idx = open(out + "/index.jsonl", "a")
for s in jl(run("competitions", "team-submissions", tid, "--format", "json")):
    for e in [e for e in jl(run("competitions", "episodes", str(s["id"]), "--format", "json")) if "COMPLETED" in e["state"]][:n]:
        f = f"{out}/episode-{e['id']}-replay.json.gz"
        if not os.path.exists(f):
            run("competitions", "replay", str(e["id"]), "-p", out, "-q")
            if os.path.exists(f[:-3]): subprocess.run(["gzip", "-f", f[:-3]])
        idx.write(json.dumps({"team_id": tid, "sub_id": s["id"], "episode_id": e["id"], "end": e["endTime"], "file": f}) + "\n"); idx.flush()
    print(s["id"], flush=True)
PY
