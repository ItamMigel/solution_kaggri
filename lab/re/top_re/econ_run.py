import sys, json, gzip, os
sys.path.insert(0, "/workspace/wt/claude/lab/re")
from kaggle_environments import make
import trades
from collections import defaultdict
def load(p):
    ns = {"__name__": "m"}; exec(compile(open(p).read(), p, "exec"), ns); return ns["agent"]
a = load(sys.argv[1]); b = load(sys.argv[2]); agg = defaultdict(float); n = 0
for seed in [int(s) for s in sys.argv[3].split(",")]:
    env = make("kaggriculture", configuration={"seed": seed}); env.run([a, b])
    rep = env.toJSON(); rep["info"]["TeamNames"] = ["topre", "es7"]; rep["info"]["seed"] = seed
    f = f"/tmp/claude-0/-workspace/94c4a2cc-e50b-475a-a250-1ec4ea3e762d/scratchpad/topre_{seed}.json"; json.dump(rep, open(f, "w"))
    g = trades.mine((f, "topre")); os.remove(f); n += 1
    for pid, step, op, item, price, inv in g["trades"]:
        if pid == 0: agg[(op, item)] += (1 if op == "SELL" else -1) * price
    agg[("FEED", "count")] += g["feed"][0]
for k, v in sorted(agg.items(), key=lambda kv: -abs(kv[1])): print(f"{k[0]:12s} {k[1]:11s} {v / n:9.0f}")
