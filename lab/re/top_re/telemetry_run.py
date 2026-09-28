import sys
from collections import Counter
from kaggle_environments import make
def load(p):
    ns = {"__name__": "m"}; exec(compile(open(p).read(), p, "exec"), ns); return ns["agent"]
a = load(sys.argv[1]); b = load(sys.argv[2]); seeds = [int(s) for s in sys.argv[3].split(",")]
for seed in seeds:
    env = make("kaggriculture", configuration={"seed": seed}); env.run([a, b])
    ops = Counter(); weeds = 0; idle = 0; moves = 0; units = 0
    for t in range(1, len(env.steps)):
        act = env.steps[t][0]["action"] or {}
        for u in [act.get("farmer")] + list(act.get("hands") or []):
            if u:
                ops[u[0]] += 1; units += 1
                idle += u[0] == "PASS"; moves += u[0] in {"NORTH", "SOUTH", "EAST", "WEST"}
    f = env.steps[-1][0]["observation"]["farms"][0]
    for row in f["tiles"]:
        for x in row: weeds += isinstance(x, dict) and x.get("kind") == "WEED"
    print(seed, "rewards", [s.reward for s in env.state],
          "idle %.3f" % (idle / max(1, units)), "move %.3f" % (moves / max(1, units)),
          "units", units, "final weeds", weeds, dict(ops.most_common(12)))
