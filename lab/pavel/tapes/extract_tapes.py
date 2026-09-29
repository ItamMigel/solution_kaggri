import gzip, json, glob, os, sys, hashlib
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
SUBS = [d.rstrip("/").split("/")[-1] for d in glob.glob("replays/5*/")]
SKIP = {"56550803", "56554450", "56651231", "56651587", "56653426", "56653430"}
def team_of(sub):
    c = Counter()
    for f in sorted(glob.glob(f"replays/{sub}/*.gz"))[:6]:
        d = json.load(gzip.open(f, "rt")); c.update(set(d["info"]["TeamNames"]))
    return c.most_common(1)[0][0]
def one(args):
    f, team = args
    try:
        d = json.load(gzip.open(f, "rt")); n = d["info"]["TeamNames"]
        if team not in n or n[0] == n[1]: return None
        p = n.index(team); q = 1 - p
        tape = [d["steps"][t + 1][p]["action"] or {} for t in range(len(d["steps"]) - 1)]
        opp_tape = [d["steps"][t + 1][q]["action"] or {} for t in range(len(d["steps"]) - 1)]
        shops = d["steps"][-1][0]["observation"]["town"].get("unlocked_shops", [])
        quads = []; prev = None
        for t, s in enumerate(d["steps"]):
            k = len(s[0]["observation"]["farms"][p].get("unlocked_quadrants") or [])
            if prev is not None and k > prev: quads.append(t)
            prev = k
        r = d["rewards"]
        return dict(file=f, team=team, seat=p, seed=d["info"]["seed"], opp=n[q], money=r[p], opp_money=r[q], shops=shops,
                    quads=quads, tape=tape, opp_tape=opp_tape)
    except Exception as e:
        return dict(file=f, err=repr(e)[:100])
if __name__ == "__main__":
    teams = {s: team_of(s) for s in SUBS if s not in SKIP}
    jobs = [(f, teams[s]) for s in teams for f in sorted(glob.glob(f"replays/{s}/*.gz"))]
    print(len(jobs), "files;", teams, flush=True)
    out = gzip.open("runs/tapes/top_tapes.jsonl.gz", "wt"); n = 0
    with ProcessPoolExecutor(64) as ex:
        for r in ex.map(one, jobs, chunksize=4):
            if r and "err" not in r:
                out.write(json.dumps(r) + "\n"); n += 1
    out.close(); print("written", n)
