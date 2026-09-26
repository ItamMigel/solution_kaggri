import sys, types
from kaggle_environments import make
def load(path):
    ns = {"__name__": "agentmod"}; exec(compile(open(path).read(), path, "exec"), ns); return ns
sw = load(sys.argv[1]); opp = load(sys.argv[2]) if sys.argv[2] != "self" else None
env = make("kaggriculture", configuration={"seed": int(sys.argv[3])})
env.run([sw["agent"], opp["agent"] if opp else load(sys.argv[1])["agent"]])
print(sys.argv[2].split("/")[-2], "rewards", [s.reward for s in env.state], "SW", sw["_SW_REPORT"])
