"""SEED-MATCHED (paired) fidelity test of the frontier imitations.

For every fresh ladder episode whose opponent belongs to a modelled archetype, we re-play the
SAME seed with the SAME agent of ours on the SAME side, substituting our imitation for the real
opponent.  The weather/market draw is therefore identical to the real game, and the comparison
"imitation vs the real thing" is paired rather than distributional -- this removes the seed
variance that makes a 3-seed mirror measurement (the 2026-08-03 method) unreliable: t_nb1's own
money ranges $91k-$140k across 6 seeds.

Usage: python pairfit.py [--cores 12] [--limit N]
"""
import argparse, json, os, statistics as st, sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/workspace/kaggriculture")
from lad2 import build, label, KEYS  # noqa: E402
from fit2 import _one  # noqa: E402

AG = "/workspace/kaggriculture/artifacts/agents"
POOL = AG + "/pool"
OURS = {"exp030": AG + "/best_exp030.py", "exp031": AG + "/best_exp031.py",
        "exp032": AG + "/best_exp032.py", "exp033": AG + "/best_exp033.py"}
IMIT = {"NB-v1": "t_nb1.py", "NB-v2 (": "t_nb2.py", "NB-partial": "t_nb_part"}   # partial resolved by money


def cls_of(r):
    lb = label(r)
    if lb.startswith("NB-v1"):
        return "nb1"
    if lb.startswith("NB-v2 ("):
        return "nb2"
    if lb.startswith("NB-partial"):
        return None       # resolved later against the class median
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cores", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(HERE, "pairfit_out.json"))
    a = ap.parse_args()

    rows = [r for r in build() if r["era"] == "NEW"]
    part = [r for r in rows if label(r).startswith("NB-partial")]
    med = st.median(r["opp_money"] for r in part) if part else 0

    jobs = []
    for r in rows:
        lb = label(r)
        if lb.startswith("NB-v1"):
            c, f = "nb1", "t_nb1.py"
        elif lb.startswith("NB-v2 ("):
            c, f = "nb2", "t_nb2.py"
        elif lb.startswith("NB-partial"):
            if r["opp_money"] <= med:
                c, f = "nblo", "t_nb_lo.py"
            else:
                c, f = "nbhi", "t_nb_hi.py"
        else:
            continue
        our = OURS.get(r["subname"])
        if not our or not os.path.exists(our):
            continue
        seed = r["o"]["seed"]
        opp_side = r["o"]["pid"]          # side the real opponent played
        imit = os.path.join(POOL, f)
        src = [None, None]
        src[opp_side] = imit
        src[1 - opp_side] = our
        jobs.append({"ep": r["ep"], "cls": c, "seed": seed, "opp_side": opp_side,
                     "our": r["subname"], "task": (src[0], src[1], seed),
                     "real_opp": r["o"], "real_us": r["u"]})
    if a.limit:
        jobs = jobs[:a.limit]
    print(f"{len(jobs)} paired counterfactual episodes to run")

    with ProcessPoolExecutor(max_workers=a.cores) as ex:
        res = list(ex.map(_one, [j["task"] for j in jobs], chunksize=1))

    out = []
    for j, fs in zip(jobs, res):
        sim_opp = fs[j["opp_side"]]
        sim_us = fs[1 - j["opp_side"]]
        out.append({"ep": j["ep"], "cls": j["cls"], "seed": j["seed"], "our": j["our"],
                    "real_opp_money": j["real_opp"]["money"], "sim_imit_money": sim_opp["money"],
                    "real_us_money": j["real_us"]["money"], "sim_us_money": sim_us["money"],
                    "real_sells": j["real_opp"]["sells"], "sim_sells": sim_opp["sells"],
                    "real_hands": j["real_opp"]["hands"], "sim_hands": sim_opp["hands"],
                    "real_bpW": j["real_opp"]["products_bought"].get("WHEAT", 0),
                    "sim_bpW": sim_opp["products_bought"].get("WHEAT", 0),
                    "real_margin_us": j["real_us"]["money"] - j["real_opp"]["money"],
                    "sim_margin_us": sim_us["money"] - sim_opp["money"]})
    json.dump(out, open(a.out, "w"), indent=1, default=float)

    print(f"\n{'class':6s} {'n':>3s} {'real opp $':>11s} {'imit $':>11s} {'fid%':>6s} "
          f"{'real our $':>11s} {'sim our $':>11s} {'real margin':>12s} {'sim margin':>12s}")
    for c in ("nb1", "nb2", "nblo", "nbhi"):
        v = [x for x in out if x["cls"] == c]
        if not v:
            continue
        ro = st.mean(x["real_opp_money"] for x in v); so = st.mean(x["sim_imit_money"] for x in v)
        ru = st.mean(x["real_us_money"] for x in v); su = st.mean(x["sim_us_money"] for x in v)
        print(f"{c:6s} {len(v):3d} {ro:11,.0f} {so:11,.0f} {100*so/ro:5.1f}% {ru:11,.0f} {su:11,.0f} "
              f"{st.mean(x['real_margin_us'] for x in v):12,.0f} {st.mean(x['sim_margin_us'] for x in v):12,.0f}")

    print("\nPRODUCTION, paired (imitation / real, same seed, same our-agent, same side)")
    for c in ("nb1", "nb2", "nblo", "nbhi"):
        v = [x for x in out if x["cls"] == c]
        if not v:
            continue
        line = []
        errs, errs_nw = [], []
        for k in KEYS:
            rr = st.mean(x["real_sells"].get(k, 0) for x in v)
            ss = st.mean(x["sim_sells"].get(k, 0) for x in v)
            line.append(f"{k[:5]}={ss:5.0f}/{rr:<5.0f}({100*ss/max(1e-9,rr):3.0f}%)")
            if rr >= 50:
                errs.append(abs(ss - rr) / rr)
                if k != "WHEAT":
                    errs_nw.append(abs(ss - rr) / rr)
        pf = 100 * (1 - st.mean(errs)) if errs else float("nan")
        pfnw = 100 * (1 - st.mean(errs_nw)) if errs_nw else float("nan")
        print(f"  {c:5s} n={len(v):3d} prod-fid {pf:5.1f}% (без пшеницы {pfnw:5.1f}%)  " + " ".join(line))
    print("\nwrote", a.out)
