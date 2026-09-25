"""Handover curve: the expert's recorded tape plays until step K, then the BC agent takes over the expert's seat
(the opponent keeps replaying its recorded tape). Final money vs the recorded expert shows in which phase BC loses value.
The BC agent is called on every step (its output ignored before K) so its history state stays consistent.

usage: python handover.py --ckpt ../../../bc3_runs/boey_r1/best.pt --glob '../../../runs/val_boey/*.gz' --team Boey \
           --ks 0,72,168,240,360,480,600,696 --out ../../../runs/handover/r1.jsonl --workers 24"""
import argparse, contextlib, glob, gzip, io, json, os, sys
from concurrent.futures import ProcessPoolExecutor

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_v] = "1"  # set before workers fork/import torch
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "bc3"))


def job(args):
    path, team, ckpt, K, sample, mix, opts, cond = args
    for v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ[v] = "1"
    from kaggle_environments import make
    import agent3
    d = json.load(gzip.open(path, "rt"))
    names = d["info"]["TeamNames"]; p = names.index(team)
    if names[0] == names[1]:
        return {"file": os.path.basename(path), "skip": "self_play"}
    tapes = [[d["steps"][k + 1][s]["action"] for k in range(len(d["steps"]) - 1)] for s in (0, 1)]
    cfg = {k: v for k, v in d["configuration"].items() if k not in ("agents", "seed")}; cfg["seed"] = d["info"]["seed"]
    bc = agent3.Agent(ckpt, sample=sample, persist="persist" in opts, dedupe="dedupe" in opts, msample="msample" in opts, fill="fill" in opts,
                         smask="smask" in opts, notrip="notrip" in opts, team=cond or None, trustop="trustop" in opts)

    def expert_seat(obs, config=None):
        k = int(obs.get("step", 0)); out = bc(obs, config)
        if k < K:
            return tapes[p][k]
        if mix == "units":  # BC units, recorded market
            return {"farmer": out["farmer"], "hands": out["hands"], "market": (tapes[p][k] or {}).get("market", [])}
        if mix == "market":  # recorded units, BC market
            t = dict(tapes[p][k] or {}); t["market"] = out["market"]; return t
        return out

    def opp_seat(obs, config=None):
        k = int(obs.get("step", 0)); return tapes[1 - p][k] if k < len(tapes[1 - p]) else {}

    agents = [expert_seat, opp_seat] if p == 0 else [opp_seat, expert_seat]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        env = make("kaggriculture", configuration=cfg, debug=False); env.run(agents)
    r = [s.reward for s in env.state]
    return {"file": os.path.basename(path), "episode": d["info"]["EpisodeId"], "K": K, "sample": sample, "mix": mix, "opts": opts,
            "rec_self": d["rewards"][p], "rec_opp": d["rewards"][1 - p], "sim_self": r[p], "sim_opp": r[1 - p],
            "status": [s.status for s in env.state]}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ckpt", required=True); ap.add_argument("--glob", required=True)
    ap.add_argument("--team", required=True); ap.add_argument("--ks", default="0,72,168,240,360,480,600,696")
    ap.add_argument("--out", required=True); ap.add_argument("--workers", type=int, default=16); ap.add_argument("--sample", action="store_true")
    ap.add_argument("--opts", default="", help="comma list: persist,dedupe")
    ap.add_argument("--cond", default="", help="multi-team model: team to condition on (data dir basename)")
    ap.add_argument("--mix", default="all", help="all | units (BC units + recorded market) | market (recorded units + BC market)")
    a = ap.parse_args(); os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    ck = ",".join(os.path.abspath(c) for c in a.ckpt.split(",") if c)
    jobs = [(f, a.team, ck, int(k), a.sample, a.mix, a.opts, a.cond) for f in sorted(glob.glob(a.glob)) for k in a.ks.split(",")]
    rows = []
    with ProcessPoolExecutor(a.workers, max_tasks_per_child=1) as ex, open(a.out, "w") as fo:
        for r in ex.map(job, jobs):
            fo.write(json.dumps(r) + "\n"); fo.flush(); rows.append(r)
    import statistics as st, collections
    by = collections.defaultdict(list)
    for r in rows:
        if "skip" not in r:
            by[r["K"]].append(r)
    print("K(step) day   n  win%   mean_self  mean_rec_self  self/rec")
    for K in sorted(by):
        R = by[K]
        print(f"{K:7} {K // 24:3} {len(R):3} {100 * sum(r['sim_self'] > r['sim_opp'] for r in R) / len(R):5.1f} "
              f"{st.mean(r['sim_self'] for r in R):11.0f} {st.mean(r['rec_self'] for r in R):14.0f} "
              f"{st.mean(r['sim_self'] for r in R) / st.mean(r['rec_self'] for r in R):8.2f}")


if __name__ == "__main__":
    main()
