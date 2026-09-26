#!/bin/bash
# ppo_rounds.sh GPU NAME INIT TEAM KL KL_FLOOR — PPO in rounds of K iterations, league refreshed each round
# (own previous snapshot + latest checkpoints of runs in $DOUBLES="run:team ..."). Extra ppo.py flags via $EXTRA_ARGS.
set -e; source "$(dirname "$0")/_env.sh"
GPU=$1; NAME=$2; INITCK=$3; TEAM=$4; KL=${5:-0.05}; FLOOR=${6:-0.0}
ROUNDS=${ROUNDS:-40}; K=${K:-10}; ENVS=${ENVS:-2048}; MB=${MB:-16384}
OUT="$RUNS/$NAME"; mkdir -p "$OUT"
for r in $(seq 1 $ROUNDS); do
  ITERS=$((r * K)); LEAGUE=(--league-snapshot "$INITCK:$TEAM")
  PREV=$(ls -t "$OUT"/it*.pt 2>/dev/null | sed -n 2p); [ -n "$PREV" ] && LEAGUE=(--league-snapshot "$PREV:$TEAM")
  for spec in $DOUBLES; do d=${spec%%:*}; t=${spec##*:}; c="$RUNS/$d/last.pt"; [ -f "$d" ] && c="$d"; [ -f "$c" ] && LEAGUE+=(--league-double "$c:$t"); done
  CUDA_VISIBLE_DEVICES=$GPU $PY "$LAB/bcppo/ppo.py" --init "$INITCK" --out "$OUT" --team $TEAM --envs $ENVS --iters $((ROUNDS * K)) --stop-at $ITERS \
     --mb $MB --amp bf16 --kl $KL --kl-floor $FLOOR --value-warmup ${WARMUP:-3} --seed $GPU --resume ${EXTRA_ARGS} "${LEAGUE[@]}" >> "$OUT/stdout.log" 2>&1 \
     || { echo "round $r failed, see $OUT/stdout.log"; exit 1; }
done
