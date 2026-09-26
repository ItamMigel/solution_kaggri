#!/bin/bash
PY=/workspace/solution_kaggri/.venv/bin/python; O=/workspace/shared/research/re; T=/workspace/shared/replays/top10v4; R=/workspace/shared/replays/reactive
run() { $PY declog.py --team "$1" --glob "$2" --out $O/$3.jsonl.gz --workers 6; }
run "Boey" "$T/*/*.gz" boey
run "M & M & P & Q" "$T/*/*.gz" mmpq
run "DSM" "$T/*/*.gz" dsm
run "Fourth Quadrant" "$T/*/*.gz" fourthq
run "DECEM" "$T/*/*.gz" decem
run "Unknown Mother-Goose" "$T/*/*.gz" mgoose
run "fuxi" "$R/fuxi/*" fuxi
run "Joseph Adamski" "$R/joseph_adamski/*" joseph
run "istinetz" "$R/istinetz/*" istinetz
run "misis biznessmenlb" "/workspace/shared/replays/ours_final/5658*/*" ours_es67
echo ALL_DONE
