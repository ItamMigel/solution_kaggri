"""Evolution strategy over Horizon v5 knobs (lab/tools/knobs.py) on the real engine.
Each generation: centre + `pairs` antithetic mutants, fresh random worlds, reactive panel, both seats (compare.py).
Fitness = mean score (W=1, D=.5, L=0) + margin/40000. Resumable: state in <out>/state.json.
usage: python knob_es.py --out /workspace/shared/runs/es1 --gens 60 --pairs 4 --worlds 8 --workers 20"""
import argparse, json, os, random, subprocess, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knobs
ROOT = "/workspace/wt/claude"; PY = "/workspace/solution_kaggri/.venv/bin/python"; POOL = "/workspace/shared/opponents/pool"
PANEL = ["--baselines", "v5_market", "--opponent", f"yhay0913={POOL}/yhay_router0913/main.py", "--opponent", f"yhay0909={POOL}/yhay_router0909/main.py",
         "--opponent", f"parthenos={POOL}/parthenos_robust/main.py", "--opponent", f"metav4={POOL}/tschinkel_metav4_v13/main.py", "--opponent", f"t2945={POOL}/tschinkel2945/main.py"]
NAMES = list(knobs.SPACE)
LO = np.array([knobs.SPACE[k][1] for k in NAMES], float); HI = np.array([knobs.SPACE[k][2] for k in NAMES], float)
def to_params(z): return {k: knobs.clip(k, LO[i] + float(np.clip(z[i], 0, 1)) * (HI[i] - LO[i])) for i, k in enumerate(NAMES)}
def z0(): return np.array([(knobs.SPACE[k][0] - LO[i]) / (HI[i] - LO[i]) for i, k in enumerate(NAMES)])

def evaluate(cands, seeds, gdir, workers):
    args = [PY, "compare.py"]
    for name, z in cands:
        knobs.make_agent_file(to_params(z), f"{gdir}/{name}/main.py"); args += ["--agent", f"{name}={gdir}/{name}/main.py"]
    args += PANEL + ["--seeds", *map(str, seeds), "--workers", str(workers), "--out", f"{gdir}/run"]
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    subprocess.run(args, cwd=ROOT, env=env, stdout=open(f"{gdir}/compare.log", "w"), stderr=subprocess.STDOUT)
    fit = {n: [] for n, _ in cands}; err = 0
    for l in open(f"{gdir}/run/games.jsonl"):
        d = json.loads(l)
        if "rewards" not in d or d.get("error"): err += 1; continue
        s = d["seat"]; m = d["rewards"][s] - d["rewards"][1 - s]
        fit[d["candidate"]].append((1.0 if m > 0 else 0.5 if m == 0 else 0.0) + m / 40000)
    return {n: float(np.mean(v)) if v else -1e9 for n, v in fit.items()}, err

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--gens", type=int, default=60)
    ap.add_argument("--pairs", type=int, default=4); ap.add_argument("--worlds", type=int, default=8); ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--sigma", type=float, default=0.12); ap.add_argument("--lr", type=float, default=0.6)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); sp = f"{a.out}/state.json"
    st = json.load(open(sp)) if os.path.exists(sp) else {"gen": 0, "mean": z0().tolist(), "sigma": a.sigma, "history": []}
    rng = random.Random(12345 + st["gen"])
    confirm = set(json.load(open(f"{ROOT}/seeds/v5_confirmation.json"))["seeds"]) | set(json.load(open(f"{ROOT}/seeds/confirmation.json"))["seeds"])
    while st["gen"] < a.gens:
        g = st["gen"]; mean = np.array(st["mean"]); sig = st["sigma"]; nprng = np.random.default_rng(1000 + g)
        eps = [nprng.standard_normal(len(NAMES)) for _ in range(a.pairs)]
        cands = [("c", mean)] + [(f"p{i}", mean + sig * e) for i, e in enumerate(eps)] + [(f"n{i}", mean - sig * e) for i, e in enumerate(eps)]
        seeds = []
        while len(seeds) < a.worlds:
            s = rng.randrange(1, 2**31 - 1)
            if s not in confirm: seeds.append(s)
        gdir = f"{a.out}/gen_{g:03d}"; os.makedirs(gdir, exist_ok=True); t0 = time.time()
        fit, err = evaluate(cands, seeds, gdir, a.workers)
        # antithetic, rank-normalised update
        diffs = np.array([fit[f"p{i}"] - fit[f"n{i}"] for i in range(a.pairs)])
        if np.any(diffs != 0):
            w = diffs / (np.abs(diffs).max() + 1e-12)
            step = sum(w[i] * eps[i] for i in range(a.pairs)) / a.pairs
            mean = np.clip(mean + a.lr * sig * step, 0, 1)
        best = max(fit, key=fit.get); bz = dict(cands)[best]
        rec = {"gen": g, "seeds": seeds, "fit": fit, "errors": err, "centre_fit": fit["c"], "best": best, "best_fit": fit[best],
               "best_params": to_params(bz), "new_mean_params": to_params(mean), "secs": round(time.time() - t0)}
        st["history"].append(rec); st["mean"] = mean.tolist(); st["gen"] = g + 1
        json.dump(st, open(sp, "w"), indent=1)
        print(json.dumps({k: rec[k] for k in ("gen", "centre_fit", "best", "best_fit", "errors", "secs")}), flush=True)

if __name__ == "__main__":
    main()
