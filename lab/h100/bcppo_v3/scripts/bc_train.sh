#!/bin/bash
# bc_train.sh GPU OUTNAME TEAMS(comma) CH BLOCKS EPOCHS  — BC v3 (team-conditioned) on data/bc_data
set -e; source "$(dirname "$0")/_env.sh"
GPU=$1; NAME=$2; TEAMS=$3; CH=${4:-128}; BLOCKS=${5:-10}; EP=${6:-20}
mkdir -p "$RUNS/$NAME"
CUDA_VISIBLE_DEVICES=$GPU $PY "$LAB/bc/train.py" --root "$BC_DATA" --data "$TEAMS" --ch $CH --blocks $BLOCKS --epochs $EP --bs ${BS:-1024} --out "$RUNS/$NAME" > "$RUNS/$NAME/stdout.log" 2>&1
echo "$NAME done: $(tail -1 "$RUNS/$NAME/stdout.log" | cut -c1-200)"
