#!/usr/bin/env python3
"""Fresh full-panel promotion gate (T025 rule): candidate vs control (es5_c3g15) on the SAME fresh worlds, both seats,
10 opponents = control itself (mirror h2h) + parthenos + metav4 + yhay0913 + t2945 + ozer_v45 + yaxon + pilkwang + es1_g9 + v5_market.
PASS = equal-weight panel paired score (cand − control) one-sided 95% lower bound > 0 AND no opponent's paired point estimate < −10pp.
usage: gate.py --cand runs/cma5/gen_005/c/main.py --out runs/gates/g005 [--worlds 16 --workers 32]"""
import argparse, json, os, random, secrets, subprocess, sys
H = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")); PKG = os.path.dirname(H); POOL = f"{PKG}/pool"
OPP = {"parthenos": "parthenos_robust", "metav4": "tschinkel_metav4_v13", "yhay0913": "yhay_router0913", "t2945": "tschinkel2945",
       "ozer_v45": "ozer_v45", "yaxon": "yaxon_reactive_v5", "pilkwang": "pilkwang_struct"}
ap = argparse.ArgumentParser(); ap.add_argument("--cand", required=True); ap.add_argument("--control", default=f"{PKG}/candidates/es5_c3g15/pkg/main.py")
ap.add_argument("--out", required=True); ap.add_argument("--worlds", type=int, default=16); ap.add_argument("--workers", type=int, default=32)
ap.add_argument("--bootstrap", type=int, default=20000); a = ap.parse_args()
out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
seeds = [secrets.randbelow(2**31 - 2) + 1 for _ in range(a.worlds)]; json.dump({"seeds": seeds}, open(f"{out}/seeds.json", "w"))
cmd = [sys.executable, "compare.py", "--agent", f"cand={os.path.abspath(a.cand)}", "--agent", f"control={os.path.abspath(a.control)}",
       "--baselines", "v5_market", "--opponent", f"mirror={os.path.abspath(a.control)}", "--opponent", f"es1_g9={PKG}/candidates/es1_g9/pkg/main.py"]
for k, v in OPP.items(): cmd += ["--opponent", f"{k}={POOL}/{v}/main.py"]
cmd += ["--seeds", *map(str, seeds), "--workers", str(a.workers), "--game-timeout", "900", "--out", f"{out}/arena"]
env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
subprocess.run(cmd, cwd=H, env=env, stdout=open(f"{out}/compare.log", "w"), stderr=subprocess.STDOUT)
pts, bad = {}, 0
for l in open(f"{out}/arena/games.jsonl"):
    r = json.loads(l)
    if r.get("error") or "points" not in r: bad += 1; continue
    pts.setdefault((r["opponent"], r["seed"]), {}).setdefault(r["candidate"], []).append(r["points"])
opps = sorted({o for o, _ in pts}); diff = {}
for (o, s), d in pts.items():
    if "cand" in d and "control" in d:
        diff.setdefault(s, {})[o] = sum(d["cand"]) / len(d["cand"]) - sum(d["control"]) / len(d["control"])
worlds = [s for s in diff if len(diff[s]) == len(opps)]
panel = [sum(diff[s].values()) / len(opps) for s in worlds]
rng = random.Random(1); boots = sorted(sum(rng.choice(panel) for _ in panel) / len(panel) for _ in range(a.bootstrap))
lower = boots[int(.05 * len(boots))]; mean = sum(panel) / len(panel)
per = {o: sum(diff[s][o] for s in worlds) / len(worlds) for o in opps}
ok = bad == 0 and lower > 0 and min(per.values()) >= -0.10
res = {"cand": os.path.abspath(a.cand), "worlds": len(worlds), "invalid_games": bad, "panel_paired_pp": 100 * mean,
       "one_sided_95_lower_pp": 100 * lower, "per_opponent_pp": {o: round(100 * v, 2) for o, v in per.items()}, "PASS": ok}
json.dump(res, open(f"{out}/gate.json", "w"), indent=1); print(json.dumps(res, indent=1))
