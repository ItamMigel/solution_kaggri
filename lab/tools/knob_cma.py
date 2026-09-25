"""CMA-ES over Horizon v5 knobs (team suggestion) — same interface/fitness as knob_es.py.
Warm start from a params.json; common fresh worlds per generation; centre evaluated each gen for reference.
usage: python knob_cma.py --init /workspace/shared/candidates_wip/es1_g13/params.json --out /workspace/shared/runs/cma1 --gens 40"""
import argparse, json, os, pickle, random, sys, time
import numpy as np, cma
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knobs, knob_es as E

PANEL4 = ["--baselines", "v5_market", "--opponent", "best=/workspace/shared/candidates/es2_c1/pkg/main.py", "--opponent", f"yhay0913={E.POOL}/yhay_router0913/main.py",
          "--opponent", f"parthenos={E.POOL}/parthenos_robust/main.py", "--opponent", f"metav4={E.POOL}/tschinkel_metav4_v13/main.py"]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--init", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--gens", type=int, default=40); ap.add_argument("--pop", type=int, default=12); ap.add_argument("--sigma", type=float, default=0.06)
    ap.add_argument("--worlds", type=int, default=8); ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--collect", action="store_true", help="append Horizon+ M1 COLLECT module to every candidate (es2_c1 family)")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); E.PANEL = PANEL4
    if a.collect:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hplus")); import modules as HM
        _orig = knobs.make_agent_file
        def _mk(params, out, base=knobs.BASE):
            ov = _orig(params, out, base); HM.build(out, {"m1_on": True, "m1_ops": ["COLLECT_FERTILIZER"]}, out); return ov
        knobs.make_agent_file = _mk
    sp = f"{a.out}/cma.pkl"; hp = f"{a.out}/history.json"
    if os.path.exists(sp):
        es = pickle.load(open(sp, "rb")); hist = json.load(open(hp))
    else:
        p0 = json.load(open(a.init)); x0 = np.array([(p0[k] - E.LO[i]) / (E.HI[i] - E.LO[i]) for i, k in enumerate(E.NAMES)])
        es = cma.CMAEvolutionStrategy(np.clip(x0, 0, 1), a.sigma, {"popsize": a.pop, "bounds": [0, 1], "seed": 7, "verbose": -9}); hist = []
    confirm = set(json.load(open(f"{E.ROOT}/seeds/v5_confirmation.json"))["seeds"]) | set(json.load(open(f"{E.ROOT}/seeds/confirmation.json"))["seeds"])
    while len(hist) < a.gens:
        g = len(hist); rng = random.Random(90210 + g); seeds = []
        while len(seeds) < a.worlds:
            s = rng.randrange(1, 2**31 - 1)
            if s not in confirm: seeds.append(s)
        X = es.ask(); centre = es.mean.copy()
        cands = [("c", centre)] + [(f"x{i}", np.asarray(x)) for i, x in enumerate(X)]
        gdir = f"{a.out}/gen_{g:03d}"; os.makedirs(gdir, exist_ok=True); t0 = time.time()
        fit, err = E.evaluate(cands, seeds, gdir, a.workers)
        es.tell(X, [-fit[f"x{i}"] for i in range(len(X))])
        best = max(fit, key=fit.get)
        rec = {"gen": g, "seeds": seeds, "fit": fit, "errors": err, "centre_fit": fit["c"], "best": best, "best_fit": fit[best],
               "sigma": float(es.sigma), "centre_params": E.to_params(centre), "best_params": E.to_params(dict(cands)[best]),
               "new_mean_params": E.to_params(es.mean), "secs": round(time.time() - t0)}
        hist.append(rec); json.dump(hist, open(hp, "w"), indent=1); pickle.dump(es, open(sp, "wb"))
        print(json.dumps({k: rec[k] for k in ("gen", "centre_fit", "best", "best_fit", "sigma", "errors", "secs")}), flush=True)

if __name__ == "__main__":
    main()
