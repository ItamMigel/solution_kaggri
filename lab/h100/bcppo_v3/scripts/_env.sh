PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -n "$PY" ]; then :; elif [ -f "$PKG/.python_path" ]; then PY="$(cat "$PKG/.python_path")"; [ -x "$PKG/$PY" ] && PY="$PKG/$PY"; else PY=python3; fi
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-4} BC_DATA="$PKG/data/bc_data"
LAB="$PKG/code/lab"; HARNESS="$PKG/code/harness"; RUNS="$PKG/runs"; INIT="${INIT:-$PKG/data/bc_ckpt/bc_v2_final.pt}"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
