"""Paired validation of a candidate NB-v1 imitation against the real 12-hand build.

Same protocol as pairfit.py, restricted to the 23 fresh episodes whose opponent is the
8 cow / 5 sheep / 12 hand build: same seed, same agent of ours, same side. The three seeds
used by the CEM are reported separately so the held-out number is visible.

Usage: python val_nb1b.py <agent.py> [--cores 12]
"""
import argparse, json, os, statistics as st, sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/workspace/kaggriculture")
from lad2 import build, label, KEYS  # noqa: E402
from fit2 import _one  # noqa: E402

AG = "/workspace/kaggriculture/artifacts/agents"
OURS = {k: f"{AG}/best_{k}.py" for k in ("exp030", "exp031", "exp032", "exp033")}
FIT_SEEDS = {1768373807, 1790493901, 900174370}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("agent")
    ap.add_argument("--cores", type=int, default=12)
    a = ap.parse_args()

    rows = [r for r in build() if r["era"] == "NEW" and label(r).startswith("NB-v1")
            and r["o"]["herd"]["COW"] == 8 and r["o"]["herd"]["SHEEP"] == 5 and r["o"]["hands"] == 12]
    jobs = []
    for r in rows:
        our = OURS.get(r["subname"])
        if not our or not os.path.exists(our):
            continue
        side = r["o"]["pid"]
        src = [None, None]
        src[side] = a.agent
        src[1 - side] = our
        jobs.append((r, (src[0], src[1], r["o"]["seed"]), side))
    print(f"{len(jobs)} paired episodes vs the 12-hand build ({a.agent})")
    with ProcessPoolExecutor(max_workers=a.cores) as ex:
        res = list(ex.map(_one, [j[1] for j in jobs], chunksize=1))

    out = []
    for (r, task, side), fs in zip(jobs, res):
        sim, us = fs[side], fs[1 - side]
        out.append({"seed": r["o"]["seed"], "held_out": r["o"]["seed"] not in FIT_SEEDS,
                    "real_opp": r["o"]["money"], "sim_opp": sim["money"],
                    "real_margin": r["u"]["money"] - r["o"]["money"],
                    "sim_margin": us["money"] - sim["money"],
                    "real_sells": r["o"]["sells"], "sim_sells": sim["sells"]})
    for tag, v in (("ALL", out), ("HELD-OUT", [x for x in out if x["held_out"]])):
        if not v:
            continue
        d = [x["sim_margin"] - x["real_margin"] for x in v]
        se = st.pstdev(d) / len(d) ** .5 if len(d) > 1 else float("nan")
        print(f"\n{tag}: n={len(v)}  opp money ${st.mean(x['sim_opp'] for x in v):,.0f} / "
              f"${st.mean(x['real_opp'] for x in v):,.0f} = {100*st.mean(x['sim_opp'] for x in v)/st.mean(x['real_opp'] for x in v):.1f}%")
        print(f"  our margin: real {st.mean(x['real_margin'] for x in v):>+9,.0f}   "
              f"sim {st.mean(x['sim_margin'] for x in v):>+9,.0f}   error {st.mean(d):>+9,.0f} ± {se:,.0f}")
        errs, errs_nw = [], []
        line = []
        for k in KEYS:
            rr = st.mean(x["real_sells"].get(k, 0) for x in v)
            ss = st.mean(x["sim_sells"].get(k, 0) for x in v)
            line.append(f"{k[:5]}={ss:5.0f}/{rr:<5.0f}({100*ss/max(1e-9,rr):3.0f}%)")
            if rr >= 50:
                errs.append(abs(ss - rr) / rr)
                if k != "WHEAT":
                    errs_nw.append(abs(ss - rr) / rr)
        print(f"  production {100*(1-st.mean(errs)):.1f}% (без пшеницы {100*(1-st.mean(errs_nw)):.1f}%)  " + " ".join(line))
    json.dump(out, open(os.path.join(HERE, "val_nb1b_out.json"), "w"), indent=1, default=float)
