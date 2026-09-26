"""Shards (declog rows of both players) -> day-level arrays for the world model and the value model.
x = macro state (15), c = [day, shops(8), opponent macro(15)], agent one-hot, y = next-day macro, margin = final reward diff."""
import glob, gzip, json, sys, numpy as np
from collections import defaultdict
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fm_data import macro, SHOPS
shards = sorted(glob.glob(sys.argv[1] + "/*.jsonl.gz")); out = sys.argv[2]
games = defaultdict(dict); agents = set()
for f in shards:
    try:
        for l in gzip.open(f, "rt"):
            r = json.loads(l)
            if r["hour"] != 2: continue
            k = (r["ep"], r.get("pl", 0), r["team"], r["opp"]); agents.add(r["team"])
            games[k][r["day"]] = (macro(r["me"]), macro(r["op"]), [sum(1 for s in r["shops"] if s == q) for q in SHOPS], r["reward"] - r["opp_reward"], r["reward"])
    except Exception as e: print("bad shard", f, e)
AG = sorted(agents); X, Y, C, A, M, V_X, V_C, V_A, V_M = [], [], [], [], [], [], [], [], []
for (ep, pl, team, opp), days in games.items():
    for d in sorted(days):
        me, op, shops, margin, rew = days[d]
        onehot = [1.0 if a == team else 0.0 for a in AG]
        V_X.append(me); V_C.append([d / 29.0] + shops + op); V_A.append(onehot); V_M.append([margin, rew])
        if d + 1 in days: X.append(me); Y.append(days[d + 1][0]); C.append([d / 29.0] + shops + op); A.append(onehot)
np.savez_compressed(out, x=np.array(X, np.float32), y=np.array(Y, np.float32), c=np.array(C, np.float32), a=np.array(A, np.float32),
                    vx=np.array(V_X, np.float32), vc=np.array(V_C, np.float32), va=np.array(V_A, np.float32), vm=np.array(V_M, np.float32), agents=np.array(AG))
print("games", len(games), "transitions", len(X), "value rows", len(V_X), "agents", AG)
