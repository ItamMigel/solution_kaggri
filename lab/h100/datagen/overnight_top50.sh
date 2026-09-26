#!/bin/bash
# wait for the top-50 download, then convert all replays (top50 + top10v4 + reactive + ours_final) into generator-format shards and zip them
while pgrep -f "[f]etch_top50.py" >/dev/null; do sleep 120; done
P=/workspace/shared/h100_pkg/kaggri_datagen; O=/workspace/shared/h100_pkg/kaggle_shards; mkdir -p $O/runs/shards_kaggle; cd $P
PY=/workspace/solution_kaggri/.venv/bin/python
$PY scripts/replays_to_shards.py '/workspace/shared/replays/top50/*/*.gz' $O/runs/shards_kaggle/top50.jsonl.gz
$PY scripts/replays_to_shards.py '/workspace/shared/replays/top10v4/*/*.gz' $O/runs/shards_kaggle/top10v4.jsonl.gz
$PY scripts/replays_to_shards.py '/workspace/shared/replays/reactive/*/*.gz' $O/runs/shards_kaggle/reactive.jsonl.gz
$PY scripts/replays_to_shards.py '/workspace/shared/replays/ours_final/*/*.gz' $O/runs/shards_kaggle/ours_ladder.jsonl.gz
cd $O && rm -f ../kaggle_shards.zip && zip -qr ../kaggle_shards.zip runs && sha256sum ../kaggle_shards.zip > ../kaggle_shards.zip.sha256
du -sh ../kaggle_shards.zip; echo OVERNIGHT_DONE
