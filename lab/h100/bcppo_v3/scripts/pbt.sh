#!/bin/bash
# PBT = evolution over PPO: 4 members (one per GPU) start from the SAME strongest checkpoint with different hyper-parameters,
# play each other in the league, and every round the CPU controller exams them in the official engine vs es3_g5/es1_g9/v5;
# the worst copies the best's weights with mutated hyper-parameters.
#   START=runs/v3_cont/it034.pt ./scripts/pbt.sh
#   OLD=/path/to/kaggri_bcppo_v2/runs  -> frozen BC doubles of dsm/mgoose/mmpq/decem/vadim join the league (gene "opps")
#   optional: PBT_TEAMS="dsm mgoose mmpq" FROZEN="$OLD/bc_v3_all/best.pt:mgoose $OLD/bc_v3_all/best.pt:mmpq"  ENVS=6256 MB=16384 K=10 WORLDS=12 WORKERS=104 (auto from nproc)
set -e; source "$(dirname "$0")/_env.sh"; S="$(dirname "$0")"
ROOT="$RUNS/pbt"; [ -n "$RESUME" ] && START=${START:-$ROOT/ref.pt}; START=${START:?set START=path/to/strongest.pt}; MEMBERS=${MEMBERS:-4}; export MEMBERS
[ -d "$ROOT" ] && [ -z "$RESUME" ] && { echo "$ROOT exists: RESUME=1 to continue, or move it away"; exit 1; }
mkdir -p "$ROOT"
# "teachers" genes: styles a member may play as (must exist in START's team list) and frozen BC team doubles for the league
OK_TEAMS=$($PY -c "import torch,sys;print(' '.join(torch.load('$START',map_location='cpu',weights_only=False).get('teams',[])))")
PBT_TEAMS=$(for t in ${PBT_TEAMS:-dsm mgoose mmpq decem vadim}; do case " $OK_TEAMS " in *" $t "*) echo -n "$t ";; esac; done)
[ -z "$FROZEN" ] && [ -n "$OLD" ] && [ -f "$OLD/bc_v3_all/best.pt" ] && FROZEN=$(for t in $PBT_TEAMS; do echo -n "$OLD/bc_v3_all/best.pt:$t "; done)
PBT_OPPS=$(for spec in $FROZEN; do echo -n "${spec##*:} "; done)
export PBT_TEAMS PBT_OPPS FROZEN; echo "teams: $PBT_TEAMS | frozen league doubles: ${PBT_OPPS:-none}"
T=($PBT_TEAMS); T0=${T[0]:-dsm}; T2=${T[1]:-$T0}; T3=${T[2]:-$T0}
if [ -z "$RESUME" ]; then
  cp "$START" "$ROOT/ref.pt"   # KL anchor (--init) and starting weights of every member
  HPS=('{"lr":5e-6,"ent":0.001,"clip":0.12,"epochs":1,"kl_floor":0.0,"target_kl":0.015,"team":"'$T0'"}'
       '{"lr":1e-5,"ent":0.001,"clip":0.12,"epochs":1,"kl_floor":0.0,"target_kl":0.02,"team":"'$T0'"}'
       '{"lr":5e-6,"ent":0.003,"clip":0.15,"epochs":2,"kl_floor":0.005,"target_kl":0.015,"team":"'$T2'"}'
       '{"lr":3e-6,"ent":0.0005,"clip":0.10,"epochs":2,"kl_floor":0.0,"target_kl":0.01,"team":"'$T3'"}')
  for i in $(seq 0 $((MEMBERS - 1))); do mkdir -p "$ROOT/m$i"; cp "$START" "$ROOT/m$i/last.pt"; echo "${HPS[$((i % 4))]}" > "$ROOT/m$i/hp.json"; done
fi
# CPU budget: the official-engine exam is the PBT bottleneck (one single-threaded game per worker).
# Leave OMP_NUM_THREADS x MEMBERS cores + 8 for the GPU trainers; on 128 cores -> ~104 workers, 12 exam worlds
# (4 members x 12 worlds x 2 seats x 3 opponents = 288 games per generation, less noisy selection).
NCPU=$(env -u OMP_NUM_THREADS nproc)   # plain nproc obeys OMP_NUM_THREADS (=4)!
Q=$(cat /sys/fs/cgroup/cpu.max 2>/dev/null); [ -n "$Q" ] && [ "${Q%% *}" != max ] && NCPU=$(( ${Q%% *} / ${Q##* } < NCPU ? ${Q%% *} / ${Q##* } : NCPU ))  # container CPU quota
 AUTO_W=$(( NCPU - OMP_NUM_THREADS * MEMBERS - 8 )); [ $AUTO_W -lt 8 ] && AUTO_W=8
WORKERS=${WORKERS:-$AUTO_W}; WORLDS=${WORLDS:-$([ $NCPU -ge 96 ] && echo 12 || echo 6)}
echo "cpus $NCPU -> exam workers $WORKERS, worlds $WORLDS"
GPUS=(${GPUS:-0 1 2 3})
for i in $(seq 0 $((MEMBERS - 1))); do nohup "$S/pbt_member.sh" $i ${GPUS[$((i % ${#GPUS[@]}))]} > "$ROOT/m$i.log" 2>&1 & done
nohup $PY "$LAB/pbt/pbt_ctl.py" --root "$ROOT" --pkg "$PKG" --py "$PY" --members $MEMBERS --worlds $WORLDS --workers $WORKERS --margin-delta ${MARGIN_DELTA:-0.03} \
  --start "$ROOT/ref.pt" >> "$ROOT/ctl.log" 2>&1 &
echo "PBT launched: tail -f $ROOT/ctl.log ; ./scripts/pbt_status.sh"
