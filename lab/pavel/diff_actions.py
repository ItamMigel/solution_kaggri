"""For a replay seat, run a reference agent on the recorded observations and dump every step where the recorded action
differs from the reference agent's action (farmer/hands/market). usage: stdin job {replay, seat, path, steps}"""
import copy, gzip, json, os, sys, io, contextlib
SHARED = ("step", "day", "hour", "farms", "market", "town")
def canon(a):
    a = json.loads(json.dumps(a if isinstance(a, dict) else {}))
    return {"farmer": a.get("farmer") or ["PASS"], "hands": a.get("hands") or [], "market": a.get("market") or []}
job = json.loads(sys.stdin.read()); sys.path.insert(0, os.path.dirname(job["path"]))
from kaggle_environments.agent import build_agent
from kaggle_environments.utils import structify
d = json.load(gzip.open(job["replay"], "rt")); q = job["seat"]; cfg = structify(d["configuration"]); diffs = []
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    ag, _ = build_agent(job["path"], {}, "kaggriculture")
    for t in range(min(job.get("steps", 719), len(d["steps"]) - 1)):
        o = copy.deepcopy(d["steps"][t][q]["observation"]); sh = d["steps"][t][0]["observation"]
        for k in SHARED:
            if k not in o and k in sh: o[k] = sh[k]
        o["player"] = q
        a = canon(ag(structify(o), cfg)); r = canon(d["steps"][t + 1][q]["action"])
        if a != r:
            diffs.append({"t": t, "day": t // 24, "units_same": a["farmer"] == r["farmer"] and a["hands"] == r["hands"],
                          "ref_market": a["market"], "rec_market": r["market"],
                          "ref_units": None if a["farmer"] == r["farmer"] and a["hands"] == r["hands"] else [a["farmer"]] + a["hands"],
                          "rec_units": None if a["farmer"] == r["farmer"] and a["hands"] == r["hands"] else [r["farmer"]] + r["hands"]})
print(json.dumps(diffs))
