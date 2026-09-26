#!/bin/bash
# v3 plan (Claude+Codex, T027). Needs the v2 run's checkpoints: OLD=/path/to/kaggri_bcppo_v2/runs ./scripts/run_all_v3.sh
#  GPU0: BC "mix" (13 teams + es3 + es3 DART, 10x128) -> closed-loop exam (export_eval) -> PPO strong_mix (team es3dart, KL floor .01)
#  GPU1: continue strong_v3 lineage from OLD/strong_v3 (new fixed code: capped market, target-KL, subset league)
#  GPU2: fresh PPO from OLD/bc_v3_all with v3 defaults (2048 envs, lr 5e-6, target-KL .015)
#  GPU3: BC Horizon-double (es3 + es3 DART only, 8x128) -> exam -> PPO double_es3 (KL floor .05 keeps Horizon style)
set -e; source "$(dirname "$0")/_env.sh"; S="$(dirname "$0")"; mkdir -p "$RUNS"
OLD=${OLD:?set OLD=/path/to/kaggri_bcppo_v2/runs}
[ -f "$OLD/bc_v3_all/best.pt" ] || { echo "missing $OLD/bc_v3_all/best.pt"; exit 1; }
ALL=$(ls "$BC_DATA" | paste -sd, -)
( "$S/bc_train.sh" 0 bc_mix "$ALL" 128 10 ${BC_EPOCHS:-20} && WORLDS=${EXAM_WORLDS:-8} "$S/export_eval.sh" "$RUNS/bc_mix/best.pt" es3dart; \
  DOUBLES="v3_cont:dsm double_es3:es3dart" "$S/ppo_rounds.sh" 0 strong_mix "$RUNS/bc_mix/best.pt" es3dart 0.05 0.01 ) > "$RUNS/gpu0.log" 2>&1 &
( V3=$(ls "$OLD"/strong_v3/it319.pt "$OLD"/strong_v3/last.pt 2>/dev/null | head -1); \
  DOUBLES="strong_mix:es3dart double_es3:es3dart" "$S/ppo_rounds.sh" 1 v3_cont "$V3" dsm 0.02 0.0 ) > "$RUNS/gpu1.log" 2>&1 &
( DOUBLES="v3_cont:dsm double_es3:es3dart" "$S/ppo_rounds.sh" 2 v3_fresh "$OLD/bc_v3_all/best.pt" dsm 0.05 0.0 ) > "$RUNS/gpu2.log" 2>&1 &
( "$S/bc_train.sh" 3 bc_es3 es3,es3dart 128 8 ${BC_EPOCHS:-20} && WORLDS=${EXAM_WORLDS:-8} "$S/export_eval.sh" "$RUNS/bc_es3/best.pt" es3dart; \
  DOUBLES="v3_cont:dsm strong_mix:es3dart" "$S/ppo_rounds.sh" 3 double_es3 "$RUNS/bc_es3/best.pt" es3dart 0.05 0.05 ) > "$RUNS/gpu3.log" 2>&1 &
[ "${AUTO_EVAL:-1}" = "1" ] && ( EVAL_WORLDS=${EVAL_WORLDS:-8} "$S/auto_eval.sh" ) > "$RUNS/auto_eval.log" 2>&1 &
echo "launched v3; ./scripts/status.sh"
