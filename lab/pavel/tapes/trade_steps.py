import gzip, json, sys
import kaggle_environments.envs.kaggriculture.kaggriculture as K
from kaggle_environments import make
f, us, d0, d1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
d = json.load(gzip.open(f, "rt")); n = d["info"]["TeamNames"]; p = n.index(us)
tapes = [[d["steps"][k + 1][s]["action"] or {} for k in range(len(d["steps"]) - 1)] for s in (0, 1)]
cfg = {k: v for k, v in d["configuration"].items() if k not in ("agents", "seed")}; cfg["seed"] = d["info"]["seed"]
log = []; cur = {"step": 0, "fids": []}
oc, opm = K._commit_unit, K._process_market
def w(op, item, price, farm, private, market, shed_capacity=100):
    ok = oc(op, item, price, farm, private, market, shed_capacity)
    if ok and item == "WHEAT": log.append((cur["step"], cur["fids"].index(id(farm)), op, price))
    return ok
def wpm(state, env):
    cur["fids"] = [id(x) for x in state[0].observation.farms]; cur["step"] = state[0].observation.step
    return opm(state, env)
K._commit_unit = w; K._process_market = wpm
def mk(t):
    return lambda obs, cfg=None: t[int(obs["step"])] if int(obs["step"]) < len(t) else {}
env = make("kaggriculture", configuration=cfg, debug=False); env.run([mk(tapes[0]), mk(tapes[1])])
from collections import defaultdict
agg = defaultdict(lambda: {0: [0, 0, 0, 0], 1: [0, 0, 0, 0]})
for st, who, op, price in log:
    a = agg[st][who]
    if op == "BUY_PRODUCT": a[0] += 1; a[1] += price
    else: a[2] += 1; a[3] += price
for st in sorted(agg):
    if not (d0 * 24 <= st < d1 * 24): continue
    u, o = agg[st][p], agg[st][1 - p]
    fmt = lambda a: f"B{a[0]:3d}@{(a[1]/a[0] if a[0] else 0):5.1f} S{a[2]:3d}@{(a[3]/a[2] if a[2] else 0):5.1f}"
    print(f"t{st} d{st//24} h{st%24:2d}  US {fmt(u)}  OPP {fmt(o)}")
