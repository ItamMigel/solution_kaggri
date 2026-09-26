#!/bin/bash
# After (or during) generation: build arrays and train world model + value model on one GPU.
#   GPU=0 ./scripts/train_gpu.sh     -> runs/models.json  (send it back to Claude; ~10-40 MB)
source "$(dirname "$0")/_env.sh"; cd "$PKG"; mkdir -p runs/shards
TPY=${TPY:-$PY}   # python with torch (e.g. the kaggri_bcppo_v3 venv)
$TPY scripts/build_dataset.py runs/shards runs/dataset.npz && \
CUDA_VISIBLE_DEVICES=${GPU:-0} $TPY scripts/train_models.py runs/dataset.npz runs/models.json ${HIDDEN:-512} ${ITERS:-60000} 2>&1 | tee runs/train.log
