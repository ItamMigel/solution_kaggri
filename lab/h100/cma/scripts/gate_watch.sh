#!/bin/bash
# Every GATE_EVERY (5) completed generations: fresh 16-world full-panel gate of that generation's centre vs es5_c3g15.
source "$(dirname "$0")/_env.sh"; NAME=$1; GW=${2:-16}; OUT="$RUNS/$NAME"
while true; do
  n=$($PY -c "import json;print(len(json.load(open('$OUT/history.json'))))" 2>/dev/null || echo 0)
  for gg in $(seq ${GATE_EVERY:-5} ${GATE_EVERY:-5} $(( n - 1 ))); do  # gen_005, gen_010, ... once completed
    c=$(printf "$OUT/gen_%03d/c/main.py" $gg); d=$(printf "$RUNS/gates/${NAME}_g%03d" $gg)
    [ -f "$c" ] && [ ! -f "$d/gate.json" ] && { echo "$(date +%F_%T) gate gen $gg"; $PY "$PKG/scripts/gate.py" --cand "$c" --out "$d" --workers $GW --worlds ${GATE_WORLDS:-16} | tail -14; }
  done
  sleep 300
done
