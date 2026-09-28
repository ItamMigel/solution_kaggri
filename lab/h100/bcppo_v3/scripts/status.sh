#!/bin/bash
source "$(dirname "$0")/_env.sh"
for d in "$RUNS"/bc_*; do [ -d "$d" ] && echo "$(basename $d): $(grep epoch "$d/stdout.log" 2>/dev/null | tail -1 | cut -c1-220)"; done
for d in "$RUNS"/strong_* "$RUNS"/double_* "$RUNS"/v3_*; do
  [ -f "$d/log.jsonl" ] || { [ -d "$d" ] && echo "$(basename $d): starting..."; continue; }
  $PY - "$d" <<'PY'
import json, sys
L = [json.loads(l) for l in open(sys.argv[1] + "/log.jsonl") if l.strip()]
f, l = L[0], L[-1]; best = max(L, key=lambda d: d["money_mean"])
g = lambda d, k: d.get(k, float("nan"))
print(f"{sys.argv[1].split('/')[-1]:12s} it {l['iter']:4d} | money {f['money_mean']:.0f} -> {l['money_mean']:.0f} (best {best['money_mean']:.0f} @{best['iter']}) | "
      f"EV {g(l,'explained_variance'):.2f} kl_bc {g(l,'kl_bc'):.4f} clipfrac {g(l,'clipfrac'):.3f} | {l['secs']}s/it | league {l.get('league_envs')}")
PY
done
ls "$RUNS"/eval 2>/dev/null | tail -8
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader
