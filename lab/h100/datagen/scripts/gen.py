"""Self-play/league data generator: plays official-engine games between our agents and the public pool and writes compact
per-step decision logs (declog format) for BOTH players, plus final rewards. No full replays.
usage: python gen.py --out runs/shards --games 20000 --workers 100"""
import argparse, gzip, json, os, random, secrets, sys, time, multiprocessing as mp
H = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); sys.path.insert(0, os.path.join(H, "scripts"))
from declog import farm_feats
from collections import Counter
AG = {"es7_wm": "candidates/es7_wm/pkg/main.py", "es6": "candidates/es6_c4g15/pkg/main.py", "es5": "candidates/es5_c3g15/pkg/main.py",
      "es3": "candidates/es3_g5/pkg/main.py", "es1_g9": "candidates/es1_g9/pkg/main.py", "top_re": "agents/top_re/main.py",
      "parthenos": "pool/parthenos_robust/main.py", "metav4": "pool/tschinkel_metav4_v13/main.py", "yhay0913": "pool/yhay_router0913/main.py",
      "t2945": "pool/tschinkel2945/main.py", "ozer": "pool/ozer_v45/main.py", "yaxon": "pool/yaxon_reactive_v5/main.py",
      "boatlee": "pool/boatlee_v16/main.py", "fukami": "pool/fukami_v48/main.py", "v5_market": "harness/agents/horizon_v5_market.py",
      "m2965": "agents/the-2965-master-hybrid-engine/main.py", "shepherd": "agents/the-shepherds-ledger-herd-safe-sovereign/main.py",
      "demand": "agents/demand-preserving-turn-sale-timing/main.py", "herdsafe": "agents/kaggriculture-herd-safe-sale-window-race-ca25/main.py",
      "top2v4": "agents/kaggriculture-top-2-master-engine-v4/main.py"}
OURS = ["es7_wm", "es6", "es5", "es3", "top_re"]; OTHERS = [k for k in AG if k not in OURS]
def matchup(rng):
    r = rng.random()
    if r < 0.45: return "es7_wm", rng.choice(OTHERS + ["es6", "es5", "es3"])
    if r < 0.55: return "es7_wm", "es7_wm"
    if r < 0.70: return "top_re", rng.choice(["es7_wm", "es6"] + OTHERS)
    if r < 0.80: return rng.choice(["es6", "es5", "es3"]), rng.choice(OTHERS)
    return rng.choice(OTHERS), rng.choice(OTHERS)
def load(name):
    p = os.path.join(H, AG[name]); ns = {"__name__": "agent_" + name, "__file__": p}
    cwd = os.getcwd(); os.chdir(os.path.dirname(p))
    try: exec(compile(open(p).read(), p, "exec"), ns)
    finally: os.chdir(cwd)
    return ns["agent"]
def rows_for(steps, p, names, rewards, gid, seed):
    out = []; o = 1 - p
    for t in range(len(steps) - 1):
        ob = steps[t][p]["observation"]; sh = steps[t][0]["observation"]
        farms = sh["farms"]; mk = sh["market"]; priv = ob.get("private") or {}
        a = steps[t + 1][p].get("action") or {}
        units = [a.get("farmer")] + list(a.get("hands") or [])
        ops = Counter((u[0] if isinstance(u, list) and u else "NONE") for u in units)
        carried = Counter()
        for inv in priv.get("inventories", []):
            for k, v in inv.items(): carried[k] += v
        out.append(dict(ep=gid, seed=seed, pl=p, team=names[p], opp=names[o], step=t, day=sh.get("day"), hour=sh.get("hour"),
                        me=farm_feats(farms[p]), op=farm_feats(farms[o]), shed=priv.get("shed", {}), seeds=priv.get("seeds", {}),
                        carried=dict(carried), prices=mk["prices"], inv=mk["inventory"], shops=(sh.get("town") or {}).get("unlocked_shops", []),
                        market=a.get("market") or [], ops=dict(ops), reward=rewards[p], opp_reward=rewards[o]))
    return out
def worker(args):
    wid, n, out, seed0 = args
    os.environ.update(OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    from kaggle_environments import make
    rng = random.Random(seed0 + wid); done = 0
    with gzip.open(f"{out}/shard_{wid:03d}_{int(time.time())}.jsonl.gz", "at") as w:
        for g in range(n):
            a, b = matchup(rng)
            if rng.random() < 0.5: a, b = b, a
            seed = secrets.randbelow(2**31 - 2) + 1; gid = f"{wid}_{g}_{seed}"
            try:
                env = make("kaggriculture", configuration={"seed": seed}); env.run([load(a), load(b)])
                steps = env.steps; rewards = [s.reward for s in env.state]
                if any(s.status != "DONE" for s in env.state) or None in rewards: continue
                for p in (0, 1):
                    for r in rows_for(steps, p, [a, b], rewards, gid, seed): w.write(json.dumps(r, separators=(",", ":")) + "\n")
                w.flush(); done += 1
            except Exception as e:
                print("game error", a, b, repr(e)[:200], flush=True)
    return done
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=os.path.join(H, "runs", "shards")); ap.add_argument("--games", type=int, default=20000)
    ap.add_argument("--workers", type=int, default=100); ap.add_argument("--seed", type=int, default=1234)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); per = max(1, a.games // a.workers)
    with mp.Pool(a.workers) as pool:
        tot = 0
        for d in pool.imap_unordered(worker, [(i, per, a.out, a.seed) for i in range(a.workers)]): tot += d; print("worker done, games so far", tot, flush=True)
    print("GEN_DONE", tot)
