"""Teacher-forced imitation diagnostic: feed a top player's recorded observations to candidate agents and
measure step-by-step agreement with the actions the top player actually took.
usage: python teacher_force.py --index <index.jsonl> --teams "DSM,M & M & P & Q" --per-team 6 --agents name=path ... --out out.jsonl --workers 20
Per (episode, player, agent): exact-match rates for whole action, farmer, hands, market, plus first divergence step
and a Counter of (recorded_op -> agent_op) mismatches for market orders."""
import argparse, collections, copy, gzip, json, os, sys
from concurrent.futures import ProcessPoolExecutor

def load_agent(path):
    from kaggle_environments.agent import get_last_callable
    src = open(path).read()
    cwd = os.getcwd(); os.chdir(os.path.dirname(os.path.abspath(path)))
    try: return get_last_callable(src, path=path)
    finally: os.chdir(cwd)

def obs_at(d, t, p):
    o = copy.deepcopy(d["steps"][t][p]["observation"]); shared = d["steps"][t][0]["observation"]
    for k in ("step", "day", "hour", "farms", "market", "town"):
        if k not in o and k in shared: o[k] = copy.deepcopy(shared[k])
    o["player"] = p; return o

def norm(a):
    return json.dumps(a if a is not None else None, sort_keys=True)

def job(args):
    rep, p, aname, apath = args
    import io, contextlib
    d = json.load(gzip.open(rep, "rt") if rep.endswith(".gz") else open(rep))
    cfg = d["configuration"]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        agent = load_agent(apath)
    n = len(d["steps"]) - 1
    tot = collections.Counter(); first = None; mm = collections.Counter(); err = 0
    for t in range(n):
        rec = d["steps"][t + 1][p]["action"] or {}
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                act = agent(obs_at(d, t, p), cfg) or {}
        except Exception:
            err += 1; act = {}
        eq = {k: norm(rec.get(k)) == norm(act.get(k)) for k in ("farmer", "hands", "market")}
        for k, v in eq.items(): tot[k] += v
        tot["all"] += all(eq.values())
        if not all(eq.values()) and first is None: first = t
        if not eq["market"]:
            ro = sorted(tuple(o[:2]) for o in (rec.get("market") or []) if isinstance(o, list))
            ao = sorted(tuple(o[:2]) for o in (act.get("market") or []) if isinstance(o, list))
            for o in set(ro) - set(ao): mm["only_top:" + "/".join(map(str, o))] += 1
            for o in set(ao) - set(ro): mm["only_agent:" + "/".join(map(str, o))] += 1
    return {"replay": os.path.basename(rep), "episode": d["info"].get("EpisodeId") or d.get("id"), "player": p,
            "name": d["info"]["TeamNames"][p], "agent": aname, "steps": n, "errors": err, "first_divergence": first,
            **{f"agree_{k}": round(tot[k] / n, 4) for k in ("all", "farmer", "hands", "market")},
            "mismatch_top": dict(mm.most_common(12))}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--index", required=True); ap.add_argument("--teams", required=True)
    ap.add_argument("--per-team", type=int, default=6); ap.add_argument("--agents", nargs="+", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--workers", type=int, default=20)
    a = ap.parse_args(); teams = [t.strip() for t in a.teams.split(",")]
    agents = [x.split("=", 1) for x in a.agents]
    per = collections.Counter(); jobs = []; seen = set()
    for l in open(a.index):
        r = json.loads(l)
        if r["episode_id"] in seen or not os.path.exists(r["file"]): continue
        seen.add(r["episode_id"])
        fp = f"/workspace/shared/research/census/fp/{r['episode_id']}.json"
        names = json.load(open(fp))["names"] if os.path.exists(fp) else json.load(gzip.open(r["file"], "rt"))["info"].get("TeamNames", [])
        for p, nm in enumerate(names):
            if nm in teams and per[nm] < a.per_team:
                per[nm] += 1
                jobs += [(r["file"], p, an, apath) for an, apath in agents]
    print(len(jobs), "jobs", dict(per), flush=True)
    with ProcessPoolExecutor(a.workers) as ex, open(a.out, "w") as f:
        for res in ex.map(job, jobs):
            f.write(json.dumps(res) + "\n"); f.flush()

if __name__ == "__main__":
    main()
