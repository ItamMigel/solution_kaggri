#!/bin/bash
set -e
cd /home/pavel-sardak/personal/kaggle/kaggriculture
until [ "$(wc -l < bc3_runs/multi15_s2/log.jsonl 2>/dev/null || echo 0)" -ge 16 ] && [ "$(wc -l < bc3_runs/multi15_s3/log.jsonl 2>/dev/null || echo 0)" -ge 16 ] && ! kill -0 997226 2>/dev/null && ! kill -0 1002426 2>/dev/null; do sleep 30; done
date -u; tail -n 1 bc3_runs/multi15_s2/log.jsonl | cut -c1-200; tail -n 1 bc3_runs/multi15_s3/log.jsonl | cut -c1-200
C=bc3_runs/multi15_s0/best.pt,bc3_runs/multi15_s1/best.pt
OMP_NUM_THREADS=4 .venv/bin/python solution/lab/pavel/bc3/export3.py --ckpt $C,bc3_runs/multi15_s2/best.pt,bc3_runs/multi15_s3/best.pt --out runs/agents/np_m15ens4_mg/main.py --fill --team mgoose_cn
OMP_NUM_THREADS=4 .venv/bin/python solution/lab/pavel/bc3/export3.py --ckpt $C,bc3_runs/multi15_s2/best.pt --out runs/agents/np_m15ens3_mg/main.py --fill --team mgoose_cn
.venv/bin/python - <<'PY'
import os
layer2 = open("runs/agents/bchg/hg_layer_v2.py").read()
orig = "_HG = {'on': True, 'slack': 3, 'buy_on': True, 'stock_hours': (0, 1, 2), 'stock_frac': 1.0, 'max_buy': 30,"
rep = orig.replace("{'on': True,", "{'on': True, 'active_last_day': 13,")
for base in ("np_m15ens4_mg", "np_m15ens3_mg"):
    bc = open(f"runs/agents/{base}/main.py").read(); d = f"runs/agents/bchg/{base}_d13"; os.makedirs(d, exist_ok=True)
    src = bc + layer2.replace(orig, rep); compile(src, base, "exec"); open(f"{d}/main.py", "w").write(src); print("built", d, len(src))
PY
cd solution
U=../research/public/agents; P=../adil-board/opponents/pool; B=../research/public_tmp/new0929b; G=../runs/agents/bchg
OMP_NUM_THREADS=1 ../.venv/bin/python compare.py --agent ens4=$G/np_m15ens4_mg_d13/main.py --agent ens3=$G/np_m15ens3_mg_d13/main.py --baselines --opponent tetsu=../research/public_tmp/tetsu1009/main.py --opponent qA=../candidates/tetsu1009_wm_qA/main.py --opponent qB=../candidates/tetsu1009_wm_qB/main.py --opponent cha22=$B/abhinav0370__cha22-agent/_extract/main.py --opponent leo3141=$B/leoprovorov__31415926535897932384626433832795058202884197169399/_extract/main.py --opponent ozer44=$U/ahmedberatozer__kaggriculture-v44-winning-the-same-turn-sale-race/main.py --opponent yaxon5=$P/yaxon_reactive_v5/main.py --opponent jaxa2802=$U/jaxa623__2802-two-identical-agents-90-points-apart/main.py --opponent v57=$U/nihilisticneuralnet__kaggriculture-population-robust-economy/main.py --opponent soil=$P/prvsiyan_soil/main.py --opponent m15ens_d13=$G/np_m15ens_mg_d13/main.py --opponent mix4_d13=$G/hg_d13/main.py --seeds-file ../runs/compare/conf_b16.json --workers 120 --game-timeout 1800 --out ../runs/compare/hg_tune5 > ../runs/compare/hg_tune5.log 2>&1
cd ..
.venv/bin/python - <<'PY'
import json
s = json.load(open("runs/compare/hg_tune5/summary.json")); s3 = json.load(open("runs/compare/hg_tune3/summary.json"))
res = {c: r["by_opponent"] for c, r in s["candidates"].items()}; res["m15ens_d13"] = s3["candidates"]["m15ens"]["by_opponent"]
C = ["m15ens_d13", "ens4", "ens3"]; O = sorted(res["ens4"])
print("%-11s" % "opp" + "".join("%11s" % c for c in C))
for o in O: print("%-11s" % o + "".join("%11.2f" % res[c].get(o, {}).get("score_rate", -1) for c in C))
F = [o for o in O if o not in ("m15ens_d13", "mix4_d13")]; tf = ("tetsu", "qA", "qB", "cha22", "leo3141"); vf = ("ozer44", "yaxon5", "jaxa2802")
for c in C:
    a = [res[c][o]["score_rate"] for o in F]; t = [res[c][o]["score_rate"] for o in tf]; v = [res[c][o]["score_rate"] for o in vf]
    print(f"{c:11} field mean {sum(a)/len(a):.3f} tetsu-fam {sum(t)/len(t):.3f} v44-fam {sum(v)/len(v):.3f}")
rows = [json.loads(l) for l in open("runs/compare/hg_tune5/games.jsonl")]
for c in ("ens4", "ens3"):
    m = sorted(r["rewards"][r["seat"]] for r in rows if r["candidate"] == c and r.get("rewards")); mx = [r.get("max_ms", [0, 0])[r["seat"]] for r in rows if r["candidate"] == c and r.get("max_ms")]
    print(c, "errors", sum(1 for r in rows if r["candidate"] == c and r.get("error")), "<70k", sum(x < 70000 for x in m), "max_ms", round(max(mx)))
PY
