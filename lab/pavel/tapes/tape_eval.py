"""Play a recorded top-team action tape open-loop (plus optional wrapper) against a live file agent in a chosen world.
worker: stdin job {tape_idx, seed, seat, opp_path, tape_file}; driver: python tape_eval.py --teams ... --n 40 --opp path --out f"""
import argparse, gzip, json, os, subprocess, sys, random
from concurrent.futures import ThreadPoolExecutor
PY = os.path.abspath(".venv/bin/python")
def worker():
    job = json.loads(sys.stdin.read())
    import io, contextlib
    from kaggle_environments import make
    from kaggle_environments.agent import build_agent
    tape = job["tape"]
    def tape_agent(obs, cfg=None):
        k = int(obs.get("step", 0) if hasattr(obs, "get") else obs.step)
        return tape[k] if 0 <= k < len(tape) else {}
    os.chdir(os.path.dirname(job["opp_path"])); sys.path.insert(0, os.path.dirname(job["opp_path"]))
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        opp, _ = build_agent(job["opp_path"], {}, "kaggriculture")
        agents = [None, None]; agents[job["seat"]] = tape_agent; agents[1 - job["seat"]] = opp
        random.seed((job["seed"] ^ 0x6D2B79F5) % 2**32)
        env = make("kaggriculture", configuration={"seed": job["seed"]}, debug=False)
        env.run(agents)
    r = [s.reward for s in env.state]
    print(json.dumps({"me": r[job["seat"]], "opp": r[1 - job["seat"]], "status": [s.status for s in env.state]}))
def run(job):
    try:
        o = subprocess.run([PY, os.path.abspath(__file__), "--worker"], input=json.dumps(job), text=True, capture_output=True, timeout=900,
                           env=dict(os.environ, OMP_NUM_THREADS="1"))
        return json.loads(o.stdout.strip().splitlines()[-1])
    except Exception as e:
        return {"err": repr(e)[:200]}
if __name__ == "__main__":
    if "--worker" in sys.argv:
        worker(); sys.exit()
    ap = argparse.ArgumentParser(); ap.add_argument("--teams", nargs="+"); ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--opp", required=True); ap.add_argument("--out", required=True); ap.add_argument("--world", default="own", choices=["own", "other"])
    ap.add_argument("--workers", type=int, default=120)
    a = ap.parse_args()
    rows = [json.loads(l) for l in gzip.open("runs/tapes/top_tapes.jsonl.gz", "rt")]
    rng = random.Random(7); jobs = []
    for team in a.teams:
        rr = sorted([r for r in rows if r["team"] == team], key=lambda r: r["file"]); rng.shuffle(rr)
        for r in rr[: a.n]:
            seed = r["seed"] if a.world == "own" else rng.randrange(1, 2**31 - 1)
            jobs.append({"team": team, "file": r["file"], "rec_money": r["money"], "rec_opp": r["opp_money"], "opp_name": r["opp"],
                         "tape": r["tape"], "seed": seed, "seat": r["seat"], "opp_path": os.path.abspath(a.opp)})
    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(run, jobs))
    with open(a.out, "w") as f:
        for j, r in zip(jobs, res):
            j = {k: v for k, v in j.items() if k != "tape"}; f.write(json.dumps(dict(j, **r)) + "\n")
    import statistics as st
    for team in a.teams:
        rr = [dict(j, **r) for j, r in zip(jobs, res) if j["team"] == team and "me" in r and r["me"] is not None]
        if not rr: print(team, "no results"); continue
        print(f"{team[:22]:22} n={len(rr)} tape money med {st.median(x['me'] for x in rr):7.0f} (recorded {st.median(x['rec_money'] for x in rr):7.0f})  "
              f"opp med {st.median(x['opp'] for x in rr):7.0f}  win {sum(x['me']>x['opp'] for x in rr)/len(rr):.2f}")
