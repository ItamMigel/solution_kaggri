#!/bin/bash
source /venv/main/bin/activate
cd /tmp/claude-0/-workspace/dc512510-85c8-45da-adba-d688751dd8b1/scratchpad
while true; do
  # only mine files not modified in the last 30s (guards against partial gz)
  files=$(find /workspace/kaggriculture/replays_mine/raw -name '*.json.gz' -mmin +0.5)
  todo=""
  for f in $files; do
    ep=$(basename "$f" | cut -d- -f2)
    [ -f /workspace/kaggriculture/replays_mine/fp/$ep.json ] || todo="$todo $f"
  done
  if [ -n "$todo" ]; then echo "$todo" | tr ' ' '\n' | grep . | xargs -P 12 -I{} python fp.py {}; fi
  if ! pgrep -f "dl.sh" >/dev/null && [ -z "$todo" ]; then echo "MINE ALL DONE"; break; fi
  sleep 20
done
