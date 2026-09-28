#!/bin/bash
# Export a checkpoint to a Kaggle agent (numpy, sampled policy) and play it in the OFFICIAL engine vs our Horizon agents.
#   ./scripts/export_eval.sh runs/ppo_gpu0/it099.pt dsm [WORLDS=8] [WORKERS=16]
set -e; source "$(dirname "$0")/_env.sh"
CK="$1"; TEAM="${2:-dsm}"; WORLDS=${WORLDS:-8}; WORKERS=${WORKERS:-16}
NAME="$(basename "$(dirname "$CK")")_$(basename "$CK" .pt)_$TEAM"; OUT="$RUNS/eval/$NAME"; mkdir -p "$OUT/agent"
$PY "$LAB/bc/export.py" --ckpt "$CK" --team "$TEAM" --out "$OUT/agent/main.py" --sample
(cd "$OUT/agent" && tar czf ../submission_$NAME.tar.gz main.py)
SEEDS=$($PY -c "import json;print(' '.join(map(str,json.load(open('$HARNESS/seeds/v5_development.json'))['seeds'][:$WORLDS])))")
cd "$HARNESS"
$PY compare.py --agent "$NAME=$OUT/agent/main.py" --baselines v5_market \
  --opponent es3_g5=candidates/es3_g5/main.py --opponent es1_g9=candidates/es1_g9/main.py --opponent yhay0913=opponents/yhay_router0913/main.py \
  --opponent parthenos=opponents/parthenos_robust/main.py --seeds $SEEDS --workers $WORKERS --game-timeout ${GAME_TIMEOUT:-900} --out "$OUT/arena_$(date +%H%M%S)" 2>&1 | tail -2
cat "$OUT"/arena_*/README.md | sed -n '/| Candidate/,/^$/p' | tail -8
echo "Kaggle archive (for the HUMAN to decide/submit): $OUT/submission_$NAME.tar.gz"
