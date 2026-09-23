#!/bin/bash
# Download replays for our own submissions, cache gzipped.
source /venv/main/bin/activate
ROOT=/workspace/kaggriculture
RAW=$ROOT/replays_mine/raw
TMP=$ROOT/replays_mine/tmp
mkdir -p "$RAW" "$TMP"
cd "$TMP" || exit 1
for ep in "$@"; do
  if [ -f "$RAW/episode-$ep-replay.json.gz" ]; then echo "cached $ep"; continue; fi
  out=$(kaggle competitions replay "$ep" 2>&1)
  if [ ! -f "episode-$ep-replay.json" ]; then
    echo "FAIL $ep :: $out"
    if echo "$out" | grep -qi "429\|rate\|too many"; then echo "RATE LIMIT - STOP"; exit 9; fi
    sleep 5
    continue
  fi
  gzip -6 -c "episode-$ep-replay.json" > "$RAW/episode-$ep-replay.json.gz"
  rm -f "episode-$ep-replay.json"
  echo "ok $ep $(du -h "$RAW/episode-$ep-replay.json.gz" | cut -f1)"
  sleep 1.5
done
