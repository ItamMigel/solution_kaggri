PKG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; H="$PKG/harness"; RUNS="$PKG/runs"
PY=${PY:-$(cat "$PKG/.python_path" 2>/dev/null || echo python3)}
NCPU=$(env -u OMP_NUM_THREADS nproc); Q=$(cat /sys/fs/cgroup/cpu.max 2>/dev/null)
[ -n "$Q" ] && [ "${Q%% *}" != max ] && NCPU=$(( ${Q%% *} / ${Q##* } < NCPU ? ${Q%% *} / ${Q##* } : NCPU ))
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PKG/pylib${PYTHONPATH:+:$PYTHONPATH}"
