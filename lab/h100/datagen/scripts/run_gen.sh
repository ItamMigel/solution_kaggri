#!/bin/bash
# Data generation on the CPU server: official-engine league games -> compact decision logs (runs/shards/*.jsonl.gz, ~80 KB/game).
#   ./scripts/run_gen.sh            # env: GAMES (20000), WORKERS (auto: CPUs - RESERVE), RESERVE (24 for PBT/CMA)
source "$(dirname "$0")/_env.sh"; cd "$PKG"; mkdir -p runs/shards
W=${WORKERS:-$(( NCPU - ${RESERVE:-24} ))}; echo "cpus $NCPU -> generator workers $W, games ${GAMES:-20000}"
nohup $PY scripts/gen.py --out runs/shards --games ${GAMES:-20000} --workers $W > runs/gen.log 2>&1 &
echo "launched: tail -f runs/gen.log ; ls runs/shards | wc -l ; du -sh runs/shards"
