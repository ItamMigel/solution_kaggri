#!/bin/bash
# pbt_member.sh I GPU — one PBT member: PPO rounds of K iterations; between rounds applies EXPLOIT.json from the controller
# (copy the donor's weights + new hyper-parameters). League = own previous snapshot + the other members' newest
# checkpoints + frozen doubles $FROZEN ("ckpt:team ...").
source "$(dirname "$0")/_env.sh"
I=$1; GPU=${2:-$1}; ROOT="$RUNS/pbt"; M="$ROOT/m$I"; REF="$ROOT/ref.pt"
K=${K:-10}; ENVS=${ENVS:-6256}; MB=${MB:-16384}; TEAM=${TEAM:-dsm}; KL=${KL:-0.02}; HORIZON=${HORIZON:-400}
# roundNNN is a member-local, monotonically increasing PBT generation.  Do not
# use PPO's itNNN here: exploit can copy a donor at an older training iteration.
r=$($PY - "$M" <<'PY'
import glob, os, re, sys
rounds = glob.glob(os.path.join(sys.argv[1], "round*.pt"))
print(1 + max((int(re.search(r"round(\d+)\.pt$", p).group(1)) for p in rounds), default=-1))
PY
)
latest_round() { ls -1 "$1"/round*.pt 2>/dev/null | sort -V | tail -1; }
ckpt_iter() {
  $PY - "$1" <<'PY'
import sys, torch
print(int(torch.load(sys.argv[1], map_location="cpu", weights_only=False)["iter"]))
PY
}
while true; do
  if [ -f "$M/EXPLOIT.json" ]; then
    $PY - "$M" <<'PY'
import json, os, sys, torch
m = sys.argv[1]; e = json.load(open(f"{m}/EXPLOIT.json"))
ck = torch.load(e["ckpt"], map_location="cpu", weights_only=False)
# PBT transfers policy/value weights and the inherited training age, but not
# Adam moments or RNG from another member.  Hyper-parameter mutation then has
# a clean optimizer state and the recipient gets its own reproducible stream.
ck.pop("optimizer", None); ck.pop("rng_cpu", None); ck.pop("rng_cuda", None)
torch.save(ck, f"{m}/last.pt.tmp"); os.replace(f"{m}/last.pt.tmp", f"{m}/last.pt")
with open(f"{m}/hp.json.tmp", "w") as f: json.dump(e["hp"], f, indent=1)
os.replace(f"{m}/hp.json.tmp", f"{m}/hp.json")
open(f"{m}/exploit.log", "a").write(json.dumps(e) + "\n")
PY
    rm -f "$M/EXPLOIT.json"; echo "$(date +%F_%T) exploited: $(tail -1 $M/exploit.log)"
  fi
  HP=$($PY -c "import json;h=json.load(open('$M/hp.json'));print(h['lr'],h['ent'],h['clip'],h['epochs'],h['kl_floor'],h['target_kl'],h.get('team','$TEAM'),','.join(h.get('opps',['*'])))")
  read LR ENT CLIP EP FLOOR TKL MTEAM OPPS <<< "$HP"
  # genome "teachers": MTEAM = style/team vector this member plays as (and is KL-anchored in);
  # OPPS = which frozen team doubles from $FROZEN are in its league ('*' = all).
  # The newest published round is exactly the frozen self-play opponent from
  # the previous round (not the second-newest, which was two rounds stale).
  OWN=$(latest_round "$M"); OT=$MTEAM; [ -n "$OWN" ] && OT=$(cat "${OWN%.pt}.team" 2>/dev/null || echo $MTEAM); [ -z "$OWN" ] && OWN="$REF"
  LEAGUE=(--league-snapshot "$OWN:$OT")
  for j in $(seq 0 $((${MEMBERS:-4} - 1))); do [ "$j" = "$I" ] && continue
    c=$(latest_round "$ROOT/m$j"); [ -z "$c" ] && continue
    jt=$(cat "${c%.pt}.team" 2>/dev/null || echo $TEAM); LEAGUE+=(--league-double "$c:$jt"); done
  for spec in $FROZEN; do [ -f "${spec%:*}" ] || continue
    case ",$OPPS," in *",*,"*|*",${spec##*:},"*) LEAGUE+=(--league-double "$spec");; esac; done
  echo "$(date +%F_%T) round $r team=$MTEAM opps=$OPPS hp lr=$LR ent=$ENT clip=$CLIP ep=$EP floor=$FLOOR tkl=$TKL league=${#LEAGUE[@]}"
  BEFORE=$(ckpt_iter "$M/last.pt")
  if CUDA_VISIBLE_DEVICES=$GPU $PY "$LAB/bcppo/ppo.py" --init "$REF" --out "$M" --team $MTEAM --envs $ENVS --iters $HORIZON --run-iters $K \
     --mb $MB --amp bf16 --kl $KL --kl-floor $FLOOR --lr $LR --ent $ENT --clip $CLIP --epochs $EP --target-kl $TKL \
     --value-warmup 0 --seed $((1000 * I + r)) --resume "${LEAGUE[@]}" >> "$M/stdout.log" 2>&1; then
    AFTER=$(ckpt_iter "$M/last.pt")
    if [ "$AFTER" -le "$BEFORE" ]; then
      echo "$(date +%F_%T) reached PPO horizon at iter $AFTER; stopping member (raise HORIZON to continue)"
      exit 0
    fi
    # Publish only after PPO exits and last.pt has atomically completed.  The
    # controller and other members never read a mutable itNNN checkpoint.
    echo "$MTEAM" > "$M/round$(printf '%03d' "$r").team"   # style this snapshot plays as (written before the .pt appears)
    $PY - "$M/last.pt" "$M/round$(printf '%03d' "$r").pt" <<'PY'
import os, shutil, sys
src, dst = sys.argv[1:]
shutil.copyfile(src, dst + ".tmp")
os.replace(dst + ".tmp", dst)
PY
    r=$((r + 1))
  else
    echo "round $r failed, see $M/stdout.log"; sleep 60
  fi
done
