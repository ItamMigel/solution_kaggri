#!/bin/bash
# Every EVAL_EVERY minutes: export the newest it*.pt of each PPO run and play it in the OFFICIAL engine (CPU) vs es1_g9/v5/yhay/parthenos.
source "$(dirname "$0")/_env.sh"; S="$(dirname "$0")"
while true; do
  for d in "$RUNS"/strong_* "$RUNS"/double_* "$RUNS"/v3_*; do
    ck=$(ls -t "$d"/it*.pt 2>/dev/null | head -1); [ -z "$ck" ] && continue
    tag="$RUNS/eval/.done_$(basename $d)_$(basename $ck)"; [ -f "$tag" ] && continue
    team=dsm; case "$(basename $d)" in double_mmpq) team=mmpq;; strong_mix|double_es3) team=es3dart;; esac
    WORLDS=${EVAL_WORLDS:-4} WORKERS=${EVAL_WORKERS:-16} "$S/export_eval.sh" "$ck" $team >> "$RUNS/auto_eval_detail.log" 2>&1 && mkdir -p "$RUNS/eval" && touch "$tag"
  done
  sleep $(( ${EVAL_EVERY:-90} * 60 ))
done
