#!/bin/bash
cd /home/pavel-sardak/personal/kaggle/kaggriculture
G=runs/agents/bchg; C=$G/np_m26ens_dsm_d13/main.py
echo "== selfplay $(date -u)"
cd solution && OMP_NUM_THREADS=1 ../.venv/bin/python compare.py --agent m26dsm=../$C --baselines --opponent self=../$C --seeds 0 --workers 2 --game-timeout 1400 --out ../runs/compare/m26dsm_selfplay > /dev/null 2>&1; cd ..
python3 -c "
import json
for l in open('runs/compare/m26dsm_selfplay/games.jsonl'):
    r=json.loads(l); print(r.get('status'), r.get('rewards'), 'calls', r.get('calls'), 'max_ms', [round(x) for x in r.get('max_ms',[])], 'invalid', r.get('invalid_steps'), r.get('error'))"
echo "== league32 $(date -u)"
cd solution; U=../research/public/agents; P=../adil-board/opponents/pool; B=../research/public_tmp/new0929b; GG=../runs/agents/bchg
OMP_NUM_THREADS=1 ../.venv/bin/python compare.py --agent m26dsm=../$C --baselines --opponent tetsu=../research/public_tmp/tetsu1009/main.py --opponent qA_ref=../candidates/tetsu1009_wm_qA/main.py --opponent qB=../candidates/tetsu1009_wm_qB/main.py --opponent cha22=$B/abhinav0370__cha22-agent/_extract/main.py --opponent leo3141=$B/leoprovorov__31415926535897932384626433832795058202884197169399/_extract/main.py --opponent v57=$U/nihilisticneuralnet__kaggriculture-population-robust-economy/main.py --opponent parthenos=$P/parthenos_robust/main.py --opponent soil=$P/prvsiyan_soil/main.py --opponent harvest=$U/haodou092__kaggriculture-harvest-ledger/main.py --opponent ozer55=$U/ahmedberatozer__kaggriculture-v55-one-turn-market-race-edge/main.py --opponent ozer44=$U/ahmedberatozer__kaggriculture-v44-winning-the-same-turn-sale-race/main.py --opponent ozer45=$P/ozer_v45/main.py --opponent yaxon5=$P/yaxon_reactive_v5/main.py --opponent jaxa2802=$U/jaxa623__2802-two-identical-agents-90-points-apart/main.py --opponent fieldcraft=$B/hakdevelopment__kaggriculture-2887-score-fieldcraft-agent/_extract/main.py --opponent es7=../adil-board/candidates/es7_wm/pkg/main.py --opponent m15ens_d13=$GG/np_m15ens_mg_d13/main.py --opponent mix4_d13=$GG/hg_d13/main.py --opponent m26mg=$GG/np_m26ens_mg_d13/main.py --seeds-file ../runs/compare/conf32.json --workers 96 --game-timeout 1800 --out ../runs/compare/m26dsm_league32 > ../runs/compare/m26dsm_league32.log 2>&1; cd ..
.venv/bin/python - <<'PY'
import json
s = json.load(open("runs/compare/m26dsm_league32/summary.json")); r = s["candidates"]["m26dsm"]["by_opponent"]
for o in sorted(r): print("%-11s %.3f %+8.0f" % (o, r[o].get("score_rate", -1), r[o].get("mean_margin", 0)))
F = [o for o in r if o not in ("m15ens_d13", "mix4_d13", "m26mg")]
print("field mean over %d: %.3f" % (len(F), sum(r[o]["score_rate"] for o in F) / len(F)))
rows = [json.loads(l) for l in open("runs/compare/m26dsm_league32/games.jsonl")]
m = sorted(x["rewards"][x["seat"]] for x in rows if x.get("rewards")); print("errors", sum(1 for x in rows if x.get("error")), "<70k", sum(v < 70000 for v in m), "median", m[len(m)//2])
PY
echo "== replay on ladder worlds $(date -u)"
cd solution/lab/pavel; R=$(cd ../../.. && pwd)
for sub in 56677106 56678587 56653430 56653426; do
  OMP_NUM_THREADS=1 ../../../.venv/bin/python replay_eval.py --glob "$R/replays/$sub/*.gz" --team 'misis biznessmenlb' --agent m26dsm=$R/$C --skip-self-play --workers 40 --out $R/runs/replay_eval/m26dsm_on_$sub.jsonl 2>&1 | grep -v pyspiel | sed -n '/^candidate/,$p' | grep -v "^---\|^columns" | sed "s/^/$sub /"
done
echo "== vs top teams $(date -u)"
OMP_NUM_THREADS=1 ../../../.venv/bin/python vs_top.py --per-team 10 --agent m26dsm=$R/$C --agent m15ens=$R/runs/agents/bchg/np_m15ens_mg_d13/main.py --workers 100 --out $R/runs/replay_eval/vs_top_m26dsm.jsonl 2>&1 | grep -v pyspiel | tail -6
echo "confirm done $(date -u)"
