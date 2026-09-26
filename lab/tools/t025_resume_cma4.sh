#!/usr/bin/env bash
# Resume CMA4 in five-generation chunks and apply the declared fresh gate.
set -euo pipefail

repo=/workspace/wt/codex
shared=/workspace/shared
python=/workspace/solution_kaggri/.venv/bin/python
out="$shared/runs/cma4"
last_label=${1:-29}

while true; do
  completed=$($python -c 'import json; print(len(json.load(open("/workspace/shared/runs/cma4/history.json"))))')
  gen=$completed
  if (( gen > last_label )); then
    break
  fi
  if (( gen % 5 != 0 )); then
    target=$((gen + 1))
    $python "$repo/lab/tools/knob_cma.py" --init "$out/init_gen15_params.json" --out "$out" \
      --gens "$target" --pop 10 --sigma 0.015 --worlds 8 --workers 14 --collect \
      --mirror "$shared/candidates/es5_c3g15/pkg/main.py"
    continue
  fi
  $python "$repo/lab/tools/knob_cma.py" --init "$out/init_gen15_params.json" --out "$out" \
    --gens "$((gen + 1))" --pop 10 --sigma 0.015 --worlds 8 --workers 14 --collect \
    --mirror "$shared/candidates/es5_c3g15/pkg/main.py"
  $python "$repo/lab/tools/t025_periodic_full_panel_gate.py" --gen "$gen" --workers 4
done
