#!/bin/bash
source "$(dirname "$0")/_env.sh"; ROOT="$RUNS/pbt"
for m in "$ROOT"/m*/; do n=$(basename $m); [ -f "$m/log.jsonl" ] || { echo "$n: starting"; continue; }
  $PY - "$m" "$n" <<'PY'
import json, sys
L = [json.loads(l) for l in open(sys.argv[1] + "log.jsonl") if l.strip()]; l = L[-1]; h = json.load(open(sys.argv[1] + "hp.json"))
g = lambda k: l.get(k, float("nan"))
print(f"{sys.argv[2]} it {l['iter']:4d} money {l['money_mean']:.0f} EV {g('explained_variance'):.2f} kl_bc {g('kl_bc'):.4f} clip {g('clipfrac'):.3f} {l['secs']}s/it | hp {h}")
PY
done
echo "--- official-engine exams (fitness = score rate + margin/40k; vs es3_g5 / es1_g9 / v5_market)"; grep -E "^gen" "$ROOT/ctl.log" | tail -${1:-12}
[ -f "$ROOT/best/best.json" ] && $PY -c "import json;b=json.load(open('$ROOT/best/best.json'));print('BEST', b['tag'], 'smooth', round(b.get('fitness_smoothed',b['fitness']),3), 'raw', round(b['fitness'],3), {o:(v['wdl'],round(v['margin'])) for o,v in b['by_opp'].items()})"
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader
