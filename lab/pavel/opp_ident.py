"""Identify which known agent a ladder opponent runs: feed the opponent's recorded observations to every candidate
agent (fresh process per (episode, candidate), cwd = agent folder, kaggle loader) and count how many of its actions
reproduce the recorded ones. A correct agent matches (nearly) every step; the rest diverge within a few steps.

usage: python opp_ident.py --replays '../../../replays/56651231/*.gz' --us 'misis biznessmenlb' \
           --cands-file cands.json --steps 200 --workers 100 --out ../../../runs/opp_ident/x.jsonl
cands.json: {"name": "path/to/main.py", ...}"""
import argparse, copy, glob, gzip, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = ("step", "day", "hour", "farms", "market", "town")


def canon(a):
    a = json.loads(json.dumps(a if isinstance(a, dict) else {}))
    return {"farmer": a.get("farmer") or ["PASS"], "hands": a.get("hands") or [], "market": a.get("market") or []}


def worker():
    job = json.loads(sys.stdin.read())
    import io, contextlib
    sys.path.insert(0, os.path.dirname(job["path"]))
    from kaggle_environments.agent import build_agent
    from kaggle_environments.utils import structify
    d = json.load(gzip.open(job["replay"], "rt")); q = job["seat"]; cfg = structify(d["configuration"])
    out = {"match": 0, "n": 0, "first_miss": None, "err": None}
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ag, _ = build_agent(job["path"], {}, "kaggriculture")
            miss = 0
            for t in range(min(job["steps"], len(d["steps"]) - 1)):
                o = copy.deepcopy(d["steps"][t][q]["observation"]); sh = d["steps"][t][0]["observation"]
                for k in SHARED:
                    if k not in o and k in sh:
                        o[k] = sh[k]
                o["player"] = q
                a = ag(structify(o), cfg)
                out["n"] += 1
                if canon(a) == canon(d["steps"][t + 1][q]["action"]):
                    out["match"] += 1
                else:
                    miss += 1
                    if out["first_miss"] is None:
                        out["first_miss"] = t
                    if miss >= job["max_miss"]:
                        break
    except BaseException as e:
        out["err"] = repr(e)[:200]
    print(json.dumps(out))


def run(job):
    try:
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "--worker"], input=json.dumps(job), text=True,
                           capture_output=True, timeout=900, cwd=os.path.dirname(job["path"]),
                           env=dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1"))
        res = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception as e:
        res = {"match": 0, "n": 0, "first_miss": None, "err": repr(e)[:200]}
    return dict(job, **res)


def main():
    if "--worker" in sys.argv:
        return worker()
    ap = argparse.ArgumentParser(); ap.add_argument("--replays", required=True); ap.add_argument("--us", required=True)
    ap.add_argument("--cands-file", required=True); ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--max-miss", type=int, default=3); ap.add_argument("--workers", type=int, default=100)
    ap.add_argument("--out", required=True); ap.add_argument("--only-nonwins", action="store_true")
    a = ap.parse_args()
    cands = {k: os.path.abspath(v) for k, v in json.load(open(a.cands_file)).items()}
    jobs = []
    for f in sorted(glob.glob(a.replays)):
        d = json.load(gzip.open(f, "rt")); n = d["info"]["TeamNames"]; r = d["rewards"]
        if n[0] == n[1] or a.us not in n:
            continue
        p = n.index(a.us); q = 1 - p
        res = "W" if r[p] > r[q] else "D" if r[p] == r[q] else "L"
        if a.only_nonwins and res == "W":
            continue
        for name, path in cands.items():
            jobs.append({"replay": os.path.abspath(f), "seat": q, "opp": n[q], "res": res, "margin": round(r[p] - r[q]),
                         "cand": name, "path": path, "steps": a.steps, "max_miss": a.max_miss})
    print(len(jobs), "jobs", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with ThreadPoolExecutor(a.workers) as ex, open(a.out, "w") as fo:
        for res in ex.map(run, jobs):
            fo.write(json.dumps(res) + "\n")
    rows = [json.loads(l) for l in open(a.out)]
    best = {}
    for r in rows:
        k = (os.path.basename(r["replay"]), r["opp"], r["res"], r["margin"])
        if k not in best or (r["match"], -(r["first_miss"] or 0)) > (best[k]["match"], -(best[k]["first_miss"] or 0)):
            best[k] = r
    for k, r in sorted(best.items(), key=lambda kv: kv[0][2]):
        print(f"{k[2]} {k[3]:+8d} {k[1][:28]:28} best={r['cand'][:40]:40} match {r['match']}/{r['n']} first_miss {r['first_miss']}")


if __name__ == "__main__":
    main()
