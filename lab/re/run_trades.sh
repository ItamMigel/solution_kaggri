#!/bin/bash
PY=/workspace/solution_kaggri/.venv/bin/python; O=/workspace/shared/research/re; T=/workspace/shared/replays/top10v4
$PY trades.py --team "M & M & P & Q" --glob "$T/mmpq/*.gz" --out $O/trades_mmpq.jsonl.gz --workers 6
$PY trades.py --team "DSM" --glob "$T/dsm/*.gz" --out $O/trades_dsm.jsonl.gz --workers 6
$PY trades.py --team "misis biznessmenlb" --glob "/workspace/shared/replays/ours_final/5658*/*.gz" --out $O/trades_ours.jsonl.gz --workers 6
$PY trades.py --team "fuxi" --glob "/workspace/shared/replays/reactive/fuxi/*.gz" --out $O/trades_fuxi.jsonl.gz --workers 6
echo TRADES_DONE
