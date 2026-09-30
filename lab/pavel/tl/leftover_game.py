import os, sys, json
from collections import Counter
from kaggle_environments import make
from kaggle_environments.agent import build_agent
path, opp_path, seed, seat = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
src = open(path).read(); ns = {"__name__": "cand"}; exec(compile(src, path, "exec"), ns)
os.chdir(os.path.dirname(opp_path)); sys.path.insert(0, os.path.dirname(opp_path)); opp, _ = build_agent(opp_path, {}, "kaggriculture")
agents = [None, None]; agents[seat] = ns["agent"]; agents[1 - seat] = opp
env = make("kaggriculture", configuration={"seed": seed}, debug=False); env.run(agents)
st = env.state; pr = st[seat].observation.private; prices = st[0].observation.market["prices"]
left = Counter({k: v for k, v in (pr.get("shed") or {}).items() if v})
for iv in pr.get("inventories") or []:
    for k, v in (iv or {}).items(): left[k] += v
val = sum(v * prices.get(k, 0) for k, v in left.items())
print(json.dumps({"agent": os.path.basename(os.path.dirname(path)), "seed": seed, "seat": seat, "rewards": [s.reward for s in st],
                  "leftover_value": val, "leftover": dict(left), "tl": ns.get("_TL_STATS")}))
