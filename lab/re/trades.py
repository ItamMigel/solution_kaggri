"""Exact executed market trades per player from replays (official engine re-run, hooks on _commit_unit / FEED).
usage: python trades.py --team Boey --glob '/workspace/shared/replays/top10v4/*/*.gz' --out /workspace/shared/research/re/trades_boey.jsonl.gz"""
import argparse, glob, gzip, json, multiprocessing as mp, os
from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as K
import kaggle_environments as KE

def load(f): return json.load(gzip.open(f, "rt")) if f.endswith(".gz") else json.load(open(f))

def mine(args):
    f, team = args
    try:
        d = load(f); names = d["info"]["TeamNames"]
        if team not in names: return None
        me = names.index(team); cfg = dict(d["configuration"]); cfg["seed"] = d["info"]["seed"]; steps = d["steps"]
        cur = {"step": 0}; refs = {}; ev = []; feed = [0, 0]; town = []
        oc, ou, ot, oi = K._commit_unit, K._apply_unit_action, K._town_consume, K.interpreter
        old = KE.core.environments["kaggriculture"]["interpreter"]
        def commit(op, item, price, farm, private, market, *extra):
            pid = refs.get(id(farm), -1); ok = oc(op, item, price, farm, private, market, *extra)
            if ok and op in ("SELL", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL"):
                ev.append((pid, cur["step"], op, item, price, market["inventory"].get(item, 0) if item in market["inventory"] else -1))
            return ok
        def unit(farm, private, idx, action, *a, **k):
            pid = refs.get(id(farm), -1)
            if isinstance(action, list) and action and action[0] == "FEED": feed[pid] += 1
            return ou(farm, private, idx, action, *a, **k)
        def tc(env, state, step):
            m = state[0].observation.market; b = dict(m["inventory"]); ot(env, state, step)
            town.append((cur["step"], {k: b[k] - m["inventory"][k] for k in b if b[k] != m["inventory"][k]}))
        def interp(state, env):
            fs = state[0].observation.farms
            if len(fs) >= 2: refs.clear(); refs.update({id(fs[0]): 0, id(fs[1]): 1})
            return oi(state, env)
        K._commit_unit, K._apply_unit_action, K._town_consume, K.interpreter = commit, unit, tc, interp
        KE.core.environments["kaggriculture"]["interpreter"] = interp
        try:
            env = make("kaggriculture", configuration=cfg, debug=False); env.reset(2)
            for t in range(1, len(steps)):
                cur["step"] = t; fs = env.state[0]["observation"]["farms"]; refs.clear(); refs.update({id(fs[0]): 0, id(fs[1]): 1})
                env.step([steps[t][p].get("action") or {} for p in range(2)])
            final = [s["reward"] for s in env.state]
        finally:
            K._commit_unit, K._apply_unit_action, K._town_consume, K.interpreter = oc, ou, ot, oi
            KE.core.environments["kaggriculture"]["interpreter"] = old
        return {"file": os.path.basename(f), "me": me, "names": names, "rewards": d["rewards"], "replayed": final,
                "trades": ev, "feed": feed, "town": town}
    except Exception as e:
        return {"file": f, "error": repr(e)}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--team"); ap.add_argument("--glob"); ap.add_argument("--out"); ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(); fs = sorted(set(glob.glob(a.glob))); n = err = 0
    with mp.Pool(a.workers) as p, gzip.open(a.out, "wt") as w:
        for r in p.imap_unordered(mine, [(f, a.team) for f in fs]):
            if r is None: continue
            if "error" in r: err += 1; print(r); continue
            w.write(json.dumps(r) + "\n"); n += 1
    print(a.team, "games", n, "errors", err)
