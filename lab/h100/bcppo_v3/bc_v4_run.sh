#!/bin/bash
# BC v4 on the CURRENT top-10 subs (fetched 2026-09-26). Run inside kaggri_bcppo_v3 after: unzip -o kaggri_bc_v4_data.zip (adds data/bc_data/<team>).
#   ./bc_v4_run.sh 2 3        # GPUs for the two BC runs (default 2 3)
set -e; cd "$(dirname "$0")"; S=./scripts; source $S/_env.sh
G1=${1:-2}; G2=${2:-3}; NEW=boey,mmpq4,dsm4,fourthq,decem4,mgoose4,azat4,seek,fish4,majkel4
OLDT=$(ls data/bc_data | grep -v -E '^(es3|es3dart|boey|mmpq4|dsm4|fourthq|decem4|mgoose4|azat4|seek|fish4|majkel4)$' | paste -sd, -)
# (a) fresh-only ablation: current top-10 only, 128x10;  (b) all: 13 old teams + current top-10, 128x12
( $S/bc_train.sh $G1 bc_v4_top "$NEW" 128 10 ${BC_EPOCHS:-20} ) > runs/bc_v4_top.log 2>&1 &
( $S/bc_train.sh $G2 bc_v4_all "$OLDT,$NEW" 128 12 ${BC_EPOCHS:-20} ) > runs/bc_v4_all.log 2>&1 &
wait
# closed-loop exam in the OFFICIAL engine for the strongest current styles (sampled policy, 8 worlds x 2 seats vs es3_g5/es1_g9/v5/yhay/parthenos)
for ck in runs/bc_v4_top/best.pt runs/bc_v4_all/best.pt; do for t in boey mmpq4 dsm4 fourthq; do
  WORLDS=${EXAM_WORLDS:-8} $S/export_eval.sh $ck $t >> runs/bc_v4_exam.log 2>&1 || true; done; done
echo BC_V4_DONE >> runs/bc_v4_exam.log
