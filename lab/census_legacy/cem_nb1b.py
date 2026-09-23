"""Fit a STRONGER NB-v1 imitation (`t_nb1b`) to the build that now dominates the ladder.

WHY: paired measurement (pairfit.py, 36 real episodes replayed on their own seeds with our own
agent on its own side) shows `t_nb1` reproduces 87.8% of NB-v1's money but only 68% of its
strawberry and 74% of its wool -- and, decisively, our champion BEATS it by +12,803 on exactly
the seeds where the real NB-v1 beats us by -18,591. A 31.4k contest error in the sub-field that
decides every verdict.

TARGET: the 8 cow / 5 sheep / 12 hand build, 23 of 36 fresh NB-v1 episodes, 23 distinct teams,
money $140,811 (target_nb1b.json).

DIFFERENCES FROM cem_fit.py (2026-08-03):
  * candidates are evaluated AGAINST OUR CHAMPION, not in a mirror. The target fingerprint was
    measured while the real agent played us; a mirror is a different market and flatters the
    imitation (t_nb1 mirror = 92% of the money, vs-champion = 78%).
  * the WHEAT line is excluded from the objective on purpose: buying ~1,000 wheat is measured at
    -$11.6k for them and cost our imitation -$30k when forced (KNOWLEDGE.md).
  * the objective carries a CONTEST term: the imitation must also reproduce the real margin
    (-23,958 for this build) against our champion, which is the thing the gate actually uses.
"""
import json, os, random, statistics as st, sys, tempfile
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/workspace/kaggriculture")
from cem_fit import SEARCH  # noqa: E402
from fit2 import _one  # noqa: E402

CHAMP = "/workspace/kaggriculture/artifacts/agents/best_exp032.py"
TGT = json.load(open(os.path.join(HERE, "target_nb1b.json")))
REAL_MARGIN = -23958.0          # our champion's real mean margin vs this build
KEYS_OBJ = ["STRAWBERRY", "MELON", "MILK", "WOOL", "FERTILIZER"]
UNIT_PRICE = {"STRAWBERRY": 205, "MELON": 249, "MILK": 150, "WOOL": 204, "FERTILIZER": 61}
SEEDS = (1768373807, 1790493901, 900174370)     # real ladder seeds from the fresh corpus


def _build_src(genome):
    import importlib.util as il
    sp = il.spec_from_file_location("_aa", "/workspace/kaggriculture/src/animal_agent.py")
    aa = il.module_from_spec(sp)
    sp.loader.exec_module(aa)
    src = aa.build_source(genome)
    p = tempfile.mktemp(suffix=".py")
    with open(p, "w") as f:
        f.write(src)
    return p


def _eval(args):
    genome, seeds = args
    try:
        path = _build_src(genome)
    except Exception as e:
        return {"err": f"{type(e).__name__}: {e}"}
    try:
        recs, margins = [], []
        for s in seeds:
            fs = _one((path, CHAMP, s))
            recs.append(fs[0])
            margins.append(fs[1]["money"] - fs[0]["money"])   # OUR margin vs the imitation
        g = lambda fn: st.mean(fn(x) for x in recs)  # noqa: E731
        return {"money": g(lambda x: x["money"]),
                "sells": {k: g(lambda x, k=k: x["sells"].get(k, 0)) for k in KEYS_OBJ},
                "margin": st.mean(margins),
                "crashed": any(sum(x["unit_ops"].values()) < 100 for x in recs)}
    except Exception as e:
        return {"err": f"{type(e).__name__}: {e}"}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def obj(a):
    num = den = 0.0
    for k in KEYS_OBJ:
        t = TGT["sells"][k]
        w = t * UNIT_PRICE[k]
        num += w * min(2.0, abs(a["sells"][k] - t) / t)
        den += w
    prod = num / den
    mon = min(1.0, abs(a["money"] - TGT["money"]) / TGT["money"])
    con = min(1.0, abs(a["margin"] - REAL_MARGIN) / 40000.0)
    return 0.50 * prod + 0.20 * mon + 0.30 * con


def cem(pinned, init, gens=6, pop=24, elite=6, workers=12):
    rng = random.Random(20260804)
    mu, sd = {}, {}
    for g, (lo, hi) in SEARCH.items():
        mu[g] = float(init[g]) if g in init else (lo + hi) / 2.0
        sd[g] = (hi - lo) / 5.0
    best = (1e9, None, None)
    for it in range(gens):
        cands = []
        for _ in range(pop):
            gm = dict(init)
            gm.update(pinned)
            for g, (lo, hi) in SEARCH.items():
                if g in pinned:
                    continue
                gm[g] = int(round(max(lo, min(hi, rng.gauss(mu[g], max(1e-6, sd[g]))))))
            cands.append(gm)
        if it == 0:
            gm = dict(init); gm.update(pinned); cands[0] = gm
        with ProcessPoolExecutor(max_workers=workers) as ex:
            out = list(ex.map(_eval, [(c, SEEDS) for c in cands]))
        scored = [(obj(a), c, a) for c, a in zip(cands, out) if "err" not in a and not a.get("crashed")]
        if not scored:
            print(f"  gen{it}: all failed:", out[0].get("err"), flush=True)
            continue
        scored.sort(key=lambda t: t[0])
        if scored[0][0] < best[0]:
            best = scored[0]
        el = scored[:elite]
        for g in SEARCH:
            if g in pinned:
                continue
            vals = [c[g] for _, c, _ in el]
            mu[g] = st.mean(vals)
            lo, hi = SEARCH[g]
            sd[g] = max((hi - lo) / 40.0, st.pstdev(vals) if len(vals) > 1 else sd[g] * 0.7)
        a = scored[0][2]
        print(f"  gen{it}: obj {scored[0][0]:.4f} money ${a['money']:>8,.0f} margin_ours {a['margin']:>+9,.0f} "
              + " ".join(f"{k[:5]}={a['sells'][k]:5.0f}/{TGT['sells'][k]:.0f}" for k in KEYS_OBJ), flush=True)
    return best


if __name__ == "__main__":
    G = json.load(open("/workspace/kaggriculture/artifacts/agents/pool/t_genomes.json"))
    init = dict(G["t_nb1"])
    PIN = {"n_cows": 8, "n_sheep": 5, "n_geese": 0, "cow_last_day": 12, "sheep_last_day": 11,
           "w_STRAWBERRY": 44, "w_MELON": 20, "w_CARROT": 0, "w_TOMATO": 0,
           "max_quadrants": 3, "fertilize_strawberry": 1, "fertilize_wheat": 1}
    best = cem(PIN, init, gens=int(sys.argv[1]) if len(sys.argv) > 1 else 6,
               pop=24, elite=6, workers=12)
    print("BEST obj", best[0])
    json.dump(best[1], open(os.path.join(HERE, "best_nb1b.json"), "w"), indent=1)
    print(json.dumps(best[2], indent=1, default=float))
