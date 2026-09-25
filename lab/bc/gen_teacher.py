"""Generate BC data from a CPU teacher agent (e.g. es3_g5 = Horizon line) playing in the official engine.
usage: python gen_teacher.py --teacher /workspace/shared/candidates/es3_g5/pkg/main.py --out /workspace/shared/bc_data/es3 --games 2000 --workers 16
Opponents rotate over a panel; teacher seat alternates. Each game -> one .npz (teacher seat) in build.py's schema."""
import argparse, io, json, os, random, sys, contextlib
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
POOL = "/workspace/shared/opponents/pool"
PANEL = {"mirror": None, "v5": "/workspace/solution_kaggri/agents/horizon_v5_market.py", "es2c1": "/workspace/shared/candidates/es2_c1/pkg/main.py",
         "yhay0913": f"{POOL}/yhay_router0913/main.py", "parthenos": f"{POOL}/parthenos_robust/main.py", "metav4": f"{POOL}/tschinkel_metav4_v13/main.py"}

def job(args):
    seed, opp, seat, teacher, out = args
    dst = f"{out}/{seed}_{opp}_{seat}.npz"
    if os.path.exists(dst): return "skip"
    try:
        import numpy as np
        random.seed(seed ^ 0x6D2B79F5); np.random.seed((seed ^ 0x6D2B79F5) & 0xFFFFFFFF)
        from kaggle_environments import make
        import build
        agents = [teacher, PANEL[opp] or teacher]
        if seat == 1: agents = agents[::-1]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            env = make("kaggriculture", configuration={"seed": seed}); env.run(agents)
        steps = json.loads(json.dumps(env.steps))
        st = [s["status"] for s in steps[-1]]
        if any(x != "DONE" for x in st): return f"ERR status {st}"
        rewards = [steps[-1][p]["reward"] for p in range(2)]
        build.encode_episode({"steps": steps, "rewards": rewards, "info": {}}, seat, dst)
        return "ok"
    except Exception as e:
        return f"ERR {e!r}"

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--teacher", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--games", type=int, default=2000); ap.add_argument("--workers", type=int, default=16); ap.add_argument("--seed0", type=int, default=31337)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    rng = random.Random(a.seed0); opps = list(PANEL)
    jobs = [(rng.randrange(1, 2**31 - 1), opps[i % len(opps)], i % 2, a.teacher, a.out) for i in range(a.games)]
    from collections import Counter
    c = Counter()
    with ProcessPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(job, jobs, chunksize=1)):
            c[r.split(" ")[0]] += 1
            if r.startswith("ERR") and c["ERR"] <= 3: print(r, flush=True)
            if i % 50 == 0: print(i, dict(c), flush=True)
    print("done", dict(c))
