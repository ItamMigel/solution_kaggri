"""Replay-eval against top teams: our candidate takes the seat OPPOSITE a top team in its recorded ladder games
(the top team's actions are replayed open-loop). usage: python vs_top.py --per-team 10 --agent n=path ... --out f"""
import argparse, gzip, json, os, random, sys, concurrent.futures, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay_eval as RE
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
ap = argparse.ArgumentParser(); ap.add_argument("--per-team", type=int, default=10); ap.add_argument("--agent", action="append", required=True)
ap.add_argument("--out", required=True); ap.add_argument("--workers", type=int, default=100); ap.add_argument("--seed", type=int, default=5)
a = ap.parse_args()
cands = [(x.split("=", 1)[0], os.path.abspath(x.split("=", 1)[1])) for x in a.agent]
rows = [json.loads(l) for l in gzip.open(os.path.join(ROOT, "runs/tapes/top_tapes.jsonl.gz"), "rt")]
rng = random.Random(a.seed); by = {}
for r in rows:
    if r["opp"] != r["team"]: by.setdefault(r["team"], []).append(r)
jobs = []
for team, rr in sorted(by.items()):
    rr = sorted(rr, key=lambda r: r["file"]); rng.shuffle(rr)
    for r in rr[: a.per_team]:
        for n, p in cands:
            jobs.append(dict(replay=os.path.join(ROOT, r["file"]), team=r["opp"], candidate=n, path=p, days=False, top=team))
print(len(jobs), "jobs", flush=True)
out = []
with concurrent.futures.ThreadPoolExecutor(a.workers) as ex, open(a.out, "w") as fo:
    futs = {ex.submit(RE.run_job, j, 1500): j for j in jobs}
    for f in concurrent.futures.as_completed(futs):
        r = f.result(); r["top"] = futs[f]["top"]; out.append(r); fo.write(json.dumps(r) + "\n"); fo.flush()
ok = [r for r in out if "error" not in r]
print("errors", len(out) - len(ok))
for n, _ in cands:
    rr = [r for r in ok if r["candidate"] == n]
    print(f"{n:10} n={len(rr)} win {sum(r['win'] for r in rr)/max(1,len(rr)):.3f}  money {sum(r['sim_cand'] for r in rr)/max(1,len(rr)):.0f} vs top {sum(r['sim_opp'] for r in rr)/max(1,len(rr)):.0f}")
    per = {}
    for r in rr: per.setdefault(r["top"], []).append(r["win"])
    print("   ", {k[:12]: f"{sum(v):.0f}/{len(v)}" for k, v in sorted(per.items())})
