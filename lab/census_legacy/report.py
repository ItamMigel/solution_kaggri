"""Final ladder-opponent report."""
import statistics as st, sys, os
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lad_analyze import build
from taxo import taxon

ANIMAL = ("MILK", "WOOL", "EGG", "FERTILIZER")
SUBLBL = {"55203378": "exp029 (LB 1132)", "55202902": "exp028 (LB 1112)", "55201960": "exp027 (LB 900)",
          "55174946": "exp023b (LB 831)", "55173278": "exp025 (LB 887)", "55173274": "exp022 (LB 914)"}


def variant(o):
    sd = o["seeds"]; bp = o["products_bought"].get("WHEAT", 0)
    car = sd.get("CARROT", 0); straw = sd.get("STRAWBERRY", 0)
    if car >= 5 and bp >= 900 and 28 <= straw <= 40: return "NB-v2 (carrot, bpW~1300)"
    if car < 3 and bp >= 700 and 40 <= straw <= 60: return "NB-v1 (frontier, straw44)"
    if bp >= 900: return "NB-v2ish"
    return "NB-partial (bpW<900)"


def label(r):
    t = taxon(r["o"])
    return variant(r["o"]) if t == "NOTEBOOK-FRONTIER FAMILY" else t


def anim_share(o):
    rev = o["sell_rev"]; tot = max(1.0, sum(rev.values()))
    return sum(rev.get(g, 0) for g in ANIMAL) / tot


def tbl(rows, keyfn, title):
    g = defaultdict(list)
    for r in rows: g[keyfn(r)].append(r)
    n = len(rows)
    print(f"\n{title}   (n={n})")
    print(f"  {'class':30s} {'n':>4s} {'share':>7s} {'teams':>6s} {'W-L':>8s} {'win%':>6s} {'mean margin':>12s} {'med opp LB':>10s}")
    for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])):
        w = sum(1 for x in v if x["win"])
        lbs = [x["opp_lb"] for x in v if x["opp_lb"]]
        print(f"  {k:30s} {len(v):4d} {100*len(v)/n:6.1f}% {len({x['opp'] for x in v}):6d} {w:3d}-{len(v)-w:<4d} {100*w/len(v):5.0f}% {st.mean(x['margin'] for x in v):12,.0f} {st.median(lbs) if lbs else 0:10.0f}")


if __name__ == "__main__":
    rows = build()
    print(f"EPISODES MINED: {len(rows)}   DISTINCT OPPONENT TEAMS: {len({r['opp'] for r in rows})}")
    print("submissions:", Counter(SUBLBL.get(r["sub"], r["sub"]) for r in rows))
    tbl(rows, lambda r: taxon(r["o"]), "A. COARSE TAXONOMY")
    tbl(rows, label, "B. FINE TAXONOMY (notebook family split)")
    for sub in sorted({r["sub"] for r in rows}):
        v = [r for r in rows if r["sub"] == sub]
        tbl(v, label, f"C. BY OUR SUBMISSION: {SUBLBL.get(sub, sub)}")
    print("\nD. r_*-MIRROR REGION OCCUPANCY")
    n = len(rows)
    for name, f in [("herd >= 20 animals", lambda o: o["n_animals"] >= 20),
                    ("herd >= 18", lambda o: o["n_animals"] >= 18),
                    ("animal revenue share >= 60%", lambda o: anim_share(o) >= 0.60),
                    ("animal revenue share >= 55%", lambda o: anim_share(o) >= 0.55),
                    ("herd>=20 AND anim>=60% (true r_*)", lambda o: o["n_animals"] >= 20 and anim_share(o) >= 0.60),
                    ("herd>=18 AND anim>=55% (loose r_*)", lambda o: o["n_animals"] >= 18 and anim_share(o) >= 0.55),
                    ("0 animals (crop-only q_*)", lambda o: o["n_animals"] == 0)]:
        v = [r for r in rows if f(r["o"])]
        w = sum(1 for x in v if x["win"])
        m = st.mean(x["margin"] for x in v) if v else 0
        print(f"  {name:38s} {len(v):4d} / {n}  = {100*len(v)/n:5.1f}%   our record {w}-{len(v)-w}   mean margin {m:>10,.0f}")
    print("\nE. HERD-SIZE DISTRIBUTION (ladder vs our pool)")
    h = Counter((r["o"]["n_animals"] // 5) * 5 for r in rows)
    for k in sorted(h):
        print(f"  {k:2d}-{k+4:2d}: {h[k]:4d} ({100*h[k]/n:5.1f}%)  {'#'*min(60,h[k])}")
    print("  our r_* pool herds: r_lean 16, r_hybrid 18, r_cow20 21, r_evo 21, r_sheep22 27, r_hold 29, r_b1x 30, r_dump 30, r_mirror 30")
    print("  our t_* pool herds: t_straw 10, t_top_hold 12, t_top4q 13, t_top1 14, t_top_grow 14")
    print("\nF. OUR RECORD BY OPPONENT LB BAND")
    b = defaultdict(list)
    for r in rows: b[int((r["opp_lb"] or 0) // 250) * 250].append(r)
    for k in sorted(b):
        v = b[k]; w = sum(1 for x in v if x["win"])
        print(f"  LB {k:5d}-{k+249:5d}: n={len(v):4d} ({100*len(v)/n:5.1f}%)  {w:3d}-{len(v)-w:<3d} ({100*w/len(v):3.0f}%)  mean margin {st.mean(x['margin'] for x in v):>10,.0f}")
    print("\nG. RATING P&L: total margin contributed by each class")
    g = defaultdict(list)
    for r in rows: g[label(r)].append(r)
    for k, v in sorted(g.items(), key=lambda kv: st.mean(x["margin"] for x in kv[1])):
        print(f"  {k:30s} n={len(v):4d}  sum margin {sum(x['margin'] for x in v):>12,.0f}   mean {st.mean(x['margin'] for x in v):>10,.0f}")
