"""Build the OLD/NEW fingerprint targets for the four frontier imitations, straight from the
mined corpora, using the 2026-08-03 class definitions (report.variant on the notebook family).
NB-partial is split lo/hi at the class median money, exactly as on 2026-08-03.
"""
import json, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lad2 import build, label, KEYS  # noqa: E402

IMIT = {"nb1": "t_nb1.py", "nb2": "t_nb2.py", "nblo": "t_nb_lo.py", "nbhi": "t_nb_hi.py"}


def profile(recs):
    g = lambda fn: st.mean(fn(x) for x in recs)  # noqa: E731
    return {"n": len(recs), "teams": len({x["name"] for x in recs}),
            "money": g(lambda x: x["money"]),
            "cow": g(lambda x: x["herd"]["COW"]), "sheep": g(lambda x: x["herd"]["SHEEP"]),
            "hands": g(lambda x: x["hands"]), "quad": g(lambda x: x["n_quad"]),
            "seeds": {k: g(lambda x, k=k: x["seeds"].get(k, 0)) for k in ("STRAWBERRY", "MELON", "WHEAT", "CARROT")},
            "sells": {k: g(lambda x, k=k: x["sells"].get(k, 0)) for k in KEYS},
            "bpWHEAT": g(lambda x: x["products_bought"].get("WHEAT", 0))}


def corpus_targets(rows):
    by = {}
    nb1 = [r["o"] for r in rows if label(r).startswith("NB-v1")]
    nb2 = [r["o"] for r in rows if label(r).startswith("NB-v2 (")]
    part = [r["o"] for r in rows if label(r).startswith("NB-partial")]
    if nb1:
        by["nb1"] = profile(nb1)
    if nb2:
        by["nb2"] = profile(nb2)
    if part:
        med = st.median(o["money"] for o in part)
        lo = [o for o in part if o["money"] <= med]
        hi = [o for o in part if o["money"] > med]
        if lo:
            by["nblo"] = profile(lo)
        if hi:
            by["nbhi"] = profile(hi)
    return by


if __name__ == "__main__":
    rows = build()
    old = corpus_targets([r for r in rows if r["era"] == "OLD"])
    new = corpus_targets([r for r in rows if r["era"] == "NEW"])
    out = {}
    for k, f in IMIT.items():
        out[k] = {"imit": f}
        if k in old:
            out[k]["old"] = old[k]
        if k in new:
            out[k]["new"] = new[k]
    json.dump(out, open(os.path.join(HERE, "targets_new.json"), "w"), indent=1)
    for k in IMIT:
        print(f"--- {k} ---")
        for era in ("old", "new"):
            p = out[k].get(era)
            if not p:
                continue
            print(f"  {era.upper()} n={p['n']:3d} teams={p['teams']:3d} money=${p['money']:>8,.0f} "
                  f"herd {p['cow']:.1f}c/{p['sheep']:.1f}s hands {p['hands']:.1f} bpW {p['bpWHEAT']:.0f}")
            print("       sold " + " ".join(f"{kk[:5]}={p['sells'][kk]:6.1f}" for kk in KEYS))
    print("wrote targets_new.json")
