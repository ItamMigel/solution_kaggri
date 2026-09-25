"""Parity: exported numpy agent (main.py) vs torch agent3.Agent on the SAME observation sequence of a recorded episode.
usage: python parity_np.py --main runs/agents/np_x/main.py --ckpt a.pt[,b.pt] --replay ep.json.gz --team NAME [--fill --smask]"""
import argparse, gzip, importlib.util, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import agent3, feat3 as F

ap = argparse.ArgumentParser(); ap.add_argument("--main", required=True); ap.add_argument("--ckpt", required=True)
ap.add_argument("--replay", required=True); ap.add_argument("--team", required=True); ap.add_argument("--steps", type=int, default=719)
ap.add_argument("--fill", action="store_true"); ap.add_argument("--smask", action="store_true"); ap.add_argument("--cond", default=None)
a = ap.parse_args()
tor = agent3.Agent(a.ckpt, fill=a.fill, smask=a.smask, team=a.cond)
spec = importlib.util.spec_from_file_location("np_main", a.main); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
npa = mod._AG
d = json.load(gzip.open(a.replay, "rt")); p = d["info"]["TeamNames"].index(a.team)
same = {"all": 0, "units": 0, "market": 0}; n = 0; first = None
for t in range(min(a.steps, len(d["steps"]) - 1)):
    o = F.merged_obs(d, t, p)
    x = tor(o); y = npa(o); n += 1
    su = [x["farmer"]] + x["hands"] == [y["farmer"]] + y["hands"]; sm = x["market"] == y["market"]
    same["units"] += su; same["market"] += sm; same["all"] += su and sm
    if first is None and not (su and sm):
        first = (t, x, y)
print({k: f"{v}/{n} ({v / n:.3f})" for k, v in same.items()})
if first:
    t, x, y = first; print("first mismatch at t", t); print(" torch:", json.dumps(x)[:300]); print(" numpy:", json.dumps(y)[:300])
