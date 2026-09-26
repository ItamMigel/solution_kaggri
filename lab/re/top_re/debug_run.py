import sys, json
from collections import Counter
from kaggle_environments import make
def load(p):
    ns = {"__name__": "m"}; exec(compile(open(p).read(), p, "exec"), ns); return ns["agent"]
a = load(sys.argv[1]); b = load(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 777
env = make("kaggriculture", configuration={"seed": seed}); env.run([a, b])
print("rewards", [s.reward for s in env.state])
for t in range(0, len(env.steps), 24 * 2):
    o = env.steps[t][0]["observation"]; f = o["farms"][0]; c = Counter()
    for row in f["tiles"]:
        for x in row:
            if isinstance(x, dict): c[x.get("crop") or x.get("animal") or x["kind"]] += 1
            elif x == "LOCKED": pass
            else: c["empty"] += 1
    act = env.steps[t + 1][0]["action"] if t + 1 < len(env.steps) else {}
    print(f"d{o['day']:2d} ${f['money']:8.0f} hands {len(f['hands'])} {dict(c)} shed {({k: v for k, v in o['private']['shed'].items() if v})} seeds {({k: v for k, v in o['private']['seeds'].items() if v})} mkt {act.get('market')}")
