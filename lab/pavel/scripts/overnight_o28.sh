#!/bin/bash
# Overnight chain 2026-09-30: official 28.09 top-vs-top episodes -> BC data -> 2 seeds -> ensemble + HG -> gate
set -e
cd /home/pavel-sardak/personal/kaggle/kaggriculture
PY=.venv/bin/python; B3=solution/lab/pavel/bc3
until [ "$(ls canon/official0928 | wc -l)" -ge 599 ] && ! pgrep -f "canon_market.py --glob data_[o]fficial" >/dev/null; do sleep 30; done
echo "canon done $(date -u)"; ls canon/official0928 | wc -l
declare -A T=( [o28_dsm_cn]="DSM" [o28_vadim_cn]="Vadim Vasilenko" [o28_mmpq_cn]="M & M & P & Q" [o28_boey_cn]="Boey" [o28_decem_cn]="DECEM" [o28_azat_cn]="Azat Akhtyamov" [o28_mgoose_cn]="Unknown Mother-Goose" [o28_victor_cn]="Victor @ Tufa Labs" [o28_majkel_cn]="Majkel1337" [o28_fourthq_cn]="Fourth Quadrant" [o28_seek_cn]="🐚seek inspiration🐚" )
NEW=""
for k in o28_dsm_cn o28_vadim_cn o28_mmpq_cn o28_boey_cn o28_decem_cn o28_azat_cn o28_mgoose_cn o28_victor_cn o28_majkel_cn o28_fourthq_cn o28_seek_cn; do
  OMP_NUM_THREADS=1 $PY $B3/build3.py --team "${T[$k]}" --glob 'data_official/1*.json' --out bc3_data/$k --canon canon/official0928 --nonoop --workers 48 2>&1 | tail -2
  echo "$k $(ls bc3_data/$k | wc -l) files"; NEW="$NEW,$(pwd)/bc3_data/$k"
done
OLD=$($PY -c "import json; print(json.load(open('bc3_runs/multi15_s0/split.json'))['args']['data'])")
DATA="$OLD$NEW"; echo "$DATA" | tr ',' '\n' | wc -l
for s in 0 1; do mkdir -p bc3_runs/multi26_s$s; OMP_NUM_THREADS=4 nohup $PY $B3/train3.py --data "$DATA" --out bc3_runs/multi26_s$s --epochs 16 --bs 256 --lr 0.001 --ch 128 --blocks 8 --hid 256 --val-eps 12 --wd 0.0001 --seed $s --cpu-board > bc3_runs/multi26_s$s/train.out 2>&1 & sleep 30; done
wait
echo "training done $(date -u)"; tail -n 1 bc3_runs/multi26_s0/log.jsonl | cut -c1-200; tail -n 1 bc3_runs/multi26_s1/log.jsonl | cut -c1-200
C=bc3_runs/multi26_s0/best.pt,bc3_runs/multi26_s1/best.pt
OMP_NUM_THREADS=4 $PY $B3/export3.py --ckpt $C --out runs/agents/np_m26ens_mg/main.py --fill --team mgoose_cn
OMP_NUM_THREADS=4 $PY $B3/export3.py --ckpt $C --out runs/agents/np_m26ens_dsm/main.py --fill --team o28_dsm_cn
$PY - <<'PY'
import os
layer2 = open("runs/agents/bchg/hg_layer_v2.py").read()
orig = "_HG = {'on': True, 'slack': 3, 'buy_on': True, 'stock_hours': (0, 1, 2), 'stock_frac': 1.0, 'max_buy': 30,"
rep = orig.replace("{'on': True,", "{'on': True, 'active_last_day': 13,")
for base in ("np_m26ens_mg", "np_m26ens_dsm"):
    bc = open(f"runs/agents/{base}/main.py").read(); d = f"runs/agents/bchg/{base}_d13"; os.makedirs(d, exist_ok=True)
    src = bc + layer2.replace(orig, rep); compile(src, base, "exec"); open(f"{d}/main.py", "w").write(src); print("built", d, len(src))
PY
cd solution
U=../research/public/agents; P=../adil-board/opponents/pool; B=../research/public_tmp/new0929b; G=../runs/agents/bchg
OMP_NUM_THREADS=1 ../.venv/bin/python compare.py --agent m26mg=$G/np_m26ens_mg_d13/main.py --agent m26dsm=$G/np_m26ens_dsm_d13/main.py --baselines --opponent tetsu=../research/public_tmp/tetsu1009/main.py --opponent qA=../candidates/tetsu1009_wm_qA/main.py --opponent qB=../candidates/tetsu1009_wm_qB/main.py --opponent cha22=$B/abhinav0370__cha22-agent/_extract/main.py --opponent leo3141=$B/leoprovorov__31415926535897932384626433832795058202884197169399/_extract/main.py --opponent ozer44=$U/ahmedberatozer__kaggriculture-v44-winning-the-same-turn-sale-race/main.py --opponent yaxon5=$P/yaxon_reactive_v5/main.py --opponent jaxa2802=$U/jaxa623__2802-two-identical-agents-90-points-apart/main.py --opponent v57=$U/nihilisticneuralnet__kaggriculture-population-robust-economy/main.py --opponent soil=$P/prvsiyan_soil/main.py --opponent m15ens_d13=$G/np_m15ens_mg_d13/main.py --opponent mix4_d13=$G/hg_d13/main.py --seeds-file ../runs/compare/conf_b16.json --workers 120 --game-timeout 1800 --out ../runs/compare/o28_gate > ../runs/compare/o28_gate.log 2>&1
cd ..
$PY - <<'PY'
import json
s = json.load(open("runs/compare/o28_gate/summary.json")); s3 = json.load(open("runs/compare/hg_tune3/summary.json"))
res = {c: r["by_opponent"] for c, r in s["candidates"].items()}; res["m15ens_d13"] = s3["candidates"]["m15ens"]["by_opponent"]
C = ["m15ens_d13", "m26mg", "m26dsm"]; O = sorted(res["m26mg"])
print("%-11s" % "opp" + "".join("%11s" % c for c in C))
for o in O: print("%-11s" % o + "".join("%11.2f" % res[c].get(o, {}).get("score_rate", -1) for c in C))
F = [o for o in O if o not in ("m15ens_d13", "mix4_d13")]; tf = ("tetsu", "qA", "qB", "cha22", "leo3141"); vf = ("ozer44", "yaxon5", "jaxa2802")
for c in C:
    a = [res[c][o]["score_rate"] for o in F]; t = [res[c][o]["score_rate"] for o in tf]; v = [res[c][o]["score_rate"] for o in vf]
    print(f"{c:11} field mean {sum(a)/len(a):.3f} tetsu-fam {sum(t)/len(t):.3f} v44-fam {sum(v)/len(v):.3f}")
rows = [json.loads(l) for l in open("runs/compare/o28_gate/games.jsonl")]
for c in ("m26mg", "m26dsm"):
    m = sorted(r["rewards"][r["seat"]] for r in rows if r["candidate"] == c and r.get("rewards"))
    print(c, "errors", sum(1 for r in rows if r["candidate"] == c and r.get("error")), "<70k", sum(x < 70000 for x in m), "median", m[len(m)//2] if m else None)
PY
echo "chain done $(date -u)"
