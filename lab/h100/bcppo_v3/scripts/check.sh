#!/bin/bash
# Sanity checks before the long run (~15 min on one GPU). All must pass.
set -e; source "$(dirname "$0")/_env.sh"; mkdir -p "$RUNS/check"
nvidia-smi --query-gpu=index,name,memory.total --format=csv
$PY -c "import torch; print('torch', torch.__version__, 'bf16:', torch.cuda.is_bf16_supported(), 'gpus', torch.cuda.device_count())"
echo "== 1/3 feature parity gpuenv vs official engine (full Horizon game) — expect all diffs ~1e-7"
$PY "$LAB/bcppo/parity_test.py" --agents "$HARNESS/agents/horizon_v5_market.py,$HARNESS/agents/horizon_v4.py" 2>&1 | grep -v pyspiel
echo "== 2/3 end-to-end: exported Kaggle agent (official engine) == GPU policy (gpuenv) — expect 'action-diff player-steps: 0' and money ~50-60k"
$PY "$LAB/bcppo/e2e_test.py" --ckpt "$INIT" --team dsm --agent "$RUNS/check/e2e_agent.py" 2>&1 | grep -v pyspiel | tail -3
echo "== 3/3 PPO smoke: 1 iteration, 64 envs, bf16, league"
$PY "$LAB/bcppo/ppo.py" --init "$INIT" --out "$RUNS/check/ppo_smoke" --envs 64 --iters 1 --mb 4096 --amp bf16 --value-warmup 0 \
   --league-snapshot "$INIT:dsm" --league-double "$INIT:mmpq" 2>&1 | grep -v pyspiel | tail -1 | cut -c1-400
echo "ALL CHECKS DONE — smoke: money_mean ~80-95k, clipfrac/approx_kl small, no errors"
