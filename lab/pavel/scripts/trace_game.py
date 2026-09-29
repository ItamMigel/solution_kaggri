import os, sys, json
from kaggle_environments import make
from kaggle_environments.agent import build_agent
seed, seat = int(sys.argv[1]), int(sys.argv[2]); a_path, o_path = os.path.abspath(sys.argv[3]), os.path.abspath(sys.argv[4])
os.chdir(os.path.dirname(o_path)); sys.path.insert(0, os.path.dirname(o_path))
opp, _ = build_agent(o_path, {}, "kaggriculture")
src = open(a_path).read(); ns = {"__name__": "cand"}; exec(compile(src, a_path, "exec"), ns)
log = []
def wrapped(obs, cfg=None):
    a = ns["agent"](obs, cfg)
    if "_HG_STATS" in ns: log.append((int(obs["step"]), dict(ns["_HG_STATS"])))
    return a
agents = [None, None]; agents[seat] = wrapped; agents[1 - seat] = opp
env = make("kaggriculture", configuration={"seed": seed}, debug=False); env.run(agents)
print("final", [s.reward for s in env.steps[-1]])
for day in range(0, 30, 2):
    t = min(day * 24 + 12, len(env.steps) - 1); o = env.steps[t][0].observation; fm = o.farms[seat]
    an = sum(1 for r in fm["tiles"] for x in r if isinstance(x, dict) and x.get("animal"))
    pl = sum(1 for r in fm["tiles"] for x in r if isinstance(x, dict) and x.get("kind") == "PLANT")
    hg = next((st for s, st in reversed(log) if s <= t), {})
    print(f"d{day:2} money {fm['money']:>7} animals {an:2} plants {pl:3} hands {len(fm.get('hands') or []):2} quads {len(fm.get('unlocked_quadrants') or [])} opp$ {o.farms[1-seat]['money']:>7} HG {hg}")
