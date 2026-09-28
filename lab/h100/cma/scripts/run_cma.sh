#!/bin/bash
# CMA-ES over the 24 Horizon knobs (+COLLECT), warm start = es5_c3g15, mirror = es5_c3g15, wide rotating panel fitness,
# + automatic fresh full-panel gate of the centre every GATE_EVERY generations.  Agents never submit.
#   ./scripts/run_cma.sh            # env: WORKERS (auto), GATE_WORKERS (auto), POP 16, WORLDS 12, SIGMA 0.015, GENS 80, NAME cma5
source "$(dirname "$0")/_env.sh"; cd "$H"
NAME=${NAME:-cma5}; OUT="$RUNS/$NAME"; mkdir -p "$OUT" "$RUNS/gates"
TOT=$(( NCPU - ${RESERVE:-24} )); GATE_WORKERS=${GATE_WORKERS:-$(( TOT / 4 ))}; WORKERS=${WORKERS:-$(( TOT - GATE_WORKERS ))}
echo "cpus $NCPU -> cma workers $WORKERS, gate workers $GATE_WORKERS (RESERVE=${RESERVE:-24} left for PBT/other)"
nohup $PY lab/tools/knob_cma.py --init "$PKG/candidates/es5_c3g15/params.json" --out "$OUT" --gens ${GENS:-80} --pop ${POP:-16} \
  --sigma ${SIGMA:-0.015} --worlds ${WORLDS:-12} --workers $WORKERS --collect --fitness panel_rotating_8 \
  --mirror "$PKG/candidates/es5_c3g15/pkg/main.py" >> "$OUT/cma.log" 2>&1 &
nohup "$PKG/scripts/gate_watch.sh" "$NAME" $GATE_WORKERS > "$RUNS/gates/watch_$NAME.log" 2>&1 &
echo "launched: tail -f $OUT/cma.log ; ./scripts/status.sh"
