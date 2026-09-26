#!/bin/bash
source "$(dirname "$0")/_env.sh"; NAME=${1:-cma6}
grep '"gen"' "$RUNS/$NAME/cma.log" | tail -${2:-8} | $PY -c "
import sys, json
for l in sys.stdin:
    d = json.loads(l); print(f\"gen {d['gen']:3d} centre {d['centre_fit']:.3f} best {d['best']} {d['best_fit']:.3f} sigma {d['sigma']:.4f} err {d['errors']} {d['secs']}s\")"
for f in "$RUNS"/gates/${NAME}_g*/gate.json; do [ -f "$f" ] && $PY -c "
import json; r = json.load(open('$f')); print('GATE', '$f'.split('/')[-2], 'PASS' if r['PASS'] else 'fail', 'panel %+.2fpp lower %+.2fpp' % (r['panel_paired_pp'], r['one_sided_95_lower_pp']), 'invalid', r['invalid_games'], r['per_opponent_pp'])"; done
true
