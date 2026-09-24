#!/bin/bash
# our own submissions' episodes (v4, v4_8turn, v3, v5 x2) -> /workspace/shared/replays/ours
cd "$(dirname "$0")"; /workspace/solution_kaggri/.venv/bin/python - <<'PY'
import json, os, subprocess
from fetch_top import run, jl
out="/workspace/shared/replays/ours"; os.makedirs(out, exist_ok=True); idx=open(out+"/index.jsonl","a")
for sid,name in [(56488922,"v4"),(56488897,"v4_8turn"),(56474100,"v3"),(56504560,"v5_market"),(56504572,"v5_guarded")]:
    for e in [e for e in jl(run("competitions","episodes",str(sid),"--format","json")) if "COMPLETED" in e["state"]][:60]:
        f=f"{out}/episode-{e['id']}-replay.json.gz"
        if not os.path.exists(f):
            run("competitions","replay",str(e["id"]),"-p",out,"-q")
            if os.path.exists(f[:-3]): subprocess.run(["gzip","-f",f[:-3]])
        idx.write(json.dumps({"team":"ours","sub":name,"sub_id":sid,"episode_id":e["id"],"end":e["endTime"],"file":f})+"\n"); idx.flush()
    print(name, flush=True)
PY
