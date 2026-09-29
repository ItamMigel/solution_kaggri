"""Re-run recorded ladder episodes from both recorded tapes (exact reproduction) with the engine's _commit_unit wrapped,
and record every executed market unit: (step, player, op, item, price). Output per-episode per-player aggregates."""
import gzip, json, os, sys, random
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
def one(args):
    f, us = args
    import kaggle_environments.envs.kaggriculture.kaggriculture as K
    from kaggle_environments import make
    d = json.load(gzip.open(f, "rt")); n = d["info"]["TeamNames"]
    if n[0] == n[1] or us not in n: return None
    p = n.index(us)
    tapes = [[d["steps"][k + 1][s]["action"] or {} for k in range(len(d["steps"]) - 1)] for s in (0, 1)]
    cfg = {k: v for k, v in d["configuration"].items() if k not in ("agents", "seed")}; cfg["seed"] = d["info"]["seed"]
    rec = d["rewards"]; del d
    log = []; cur = {"step": 0}
    orig = K._commit_unit; orig_pm = K._process_market
    def wrapped(op, item, price, farm, private, market, shed_capacity=100):
        ok = orig(op, item, price, farm, private, market, shed_capacity)
        if ok:
            fids = cur.get("fids") or []
            log.append((cur["step"], fids.index(id(farm)) if id(farm) in fids else -1, op, item, price))
        return ok
    def wrapped_pm(state, env):
        cur["fids"] = [id(f) for f in state[0].observation.farms]
        return orig_pm(state, env)
    K._commit_unit = wrapped; K._process_market = wrapped_pm
    def mk(tape, seat):
        def ag(obs, config=None):
            k = int(obs.get("step", 0)) if hasattr(obs, "get") else int(obs.step)
            if seat == 0: cur["step"] = k
            return tape[k] if 0 <= k < len(tape) else {}
        return ag
    env = make("kaggriculture", configuration=cfg, debug=False)
    env.reset(2)
    farm_ids = None
    # run step by step to learn which farm object belongs to whom
    agents = [mk(tapes[0], 0), mk(tapes[1], 1)]
    env.run(agents)
    rew = [s.reward for s in env.state]
    # identify farm ids: the engine keeps the same farm dicts in obs0.farms
    agg = [defaultdict(float) for _ in range(2)]
    for step, who, op, item, price in log:
        if who < 0: continue
        key = f"{op}:{item}"; agg[who][key + ":units"] += 1; agg[who][key + ":value"] += price
        day = step // 24; agg[who][f"{op}:{item}:d{day}:value"] += price; agg[who][f"{op}:{item}:d{day}:units"] += 1
    return {"file": f, "us": p, "rec": rec, "sim": rew, "exact": rew == rec, "agg": [dict(a) for a in agg], "unattributed": sum(1 for x in log if x[1] < 0)}
if __name__ == "__main__":
    import glob
    files = sorted(glob.glob(sys.argv[1])); us = sys.argv[2]; out = sys.argv[3]
    with ProcessPoolExecutor(64) as ex, open(out, "w") as fo:
        for r in ex.map(one, [(f, us) for f in files]):
            if r: fo.write(json.dumps(r) + "\n")
    rows = [json.loads(l) for l in open(out)]
    print(len(rows), "episodes; exact reproduction", sum(r["exact"] for r in rows))
