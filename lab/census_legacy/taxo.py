"""Mechanism-based taxonomy of ladder opponents + our record per type."""
import json, glob, os, sys, statistics as st
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lad_analyze import build

ANIMAL = ("MILK", "WOOL", "EGG", "FERTILIZER")


def shares(r):
    rev = r["sell_rev"]
    tot = max(1.0, sum(rev.values()))
    return {k: v / tot for k, v in rev.items()}, tot


def taxon(r):
    sh, tot = shares(r)
    na = r["n_animals"]
    anim = sum(sh.get(g, 0) for g in ANIMAL)
    straw = sh.get("STRAWBERRY", 0)
    mel = sh.get("MELON", 0)
    wheatbuy = r["products_bought"].get("WHEAT", 0)
    unit_ops = sum(r["unit_ops"].values())
    if unit_ops < 200 or tot < 3000:
        return "WEAK/BROKEN"
    if na == 0:
        return "CROP-ONLY"
    if na >= 20:
        return "BIG-HERD ANIMAL (>=20)"
    # the public "notebook" family: small/medium herd fed by BOUGHT wheat, strawberry-led
    if wheatbuy >= 250 and na >= 5 and straw >= 0.08:
        return "NOTEBOOK-FRONTIER FAMILY"
    if anim >= 0.55 and na >= 8:
        return "MID-HERD ANIMAL-LED"
    if mel >= 0.35:
        return "MELON-RUSH + small herd"
    return "OTHER MIXED"


def nb_variant(r):
    sd = r["seeds"]
    return "v2(+carrot)" if sd.get("CARROT", 0) >= 5 else "v1(no carrot)"


if __name__ == "__main__":
    rows = build()
    for r in rows:
        r["tax"] = taxon(r["o"])
        sh, tot = shares(r["o"])
        r["opp_anim_share"] = sum(sh.get(g, 0) for g in ANIMAL)
        r["opp_straw_share"] = sh.get("STRAWBERRY", 0)
        r["opp_rev"] = tot
    n = len(rows)
    print(f"=== {n} ladder episodes, {len({r['opp'] for r in rows})} distinct opponent teams ===\n")
    print(f"{'TYPE':30s} {'n':>4s} {'%':>6s} {'W-L':>7s} {'winrate':>8s} {'mean margin':>12s} {'median LB':>10s}")
    by = defaultdict(list)
    for r in rows:
        by[r["tax"]].append(r)
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        w = sum(1 for x in v if x["win"]); l = len(v) - w
        mg = st.mean(x["margin"] for x in v)
        lbs = [x["opp_lb"] for x in v if x["opp_lb"]]
        print(f"{k:30s} {len(v):4d} {100*len(v)/n:5.1f}% {w:3d}-{l:<3d} {100*w/len(v):7.1f}% {mg:12,.0f} {st.median(lbs) if lbs else 0:10.0f}")
    print()
    nb = [r for r in rows if r["tax"] == "NOTEBOOK-FRONTIER FAMILY"]
    c = Counter(nb_variant(r["o"]) for r in nb)
    print("notebook variants:", dict(c))
    print()
    print("--- our record by our submission (rating band) ---")
    bys = defaultdict(list)
    for r in rows:
        bys[r["sub"]].append(r)
    for k, v in sorted(bys.items()):
        w = sum(1 for x in v if x["win"])
        print(f"  sub {k}: {len(v):3d} eps  {w}-{len(v)-w}  ({100*w/len(v):.0f}%)  mean margin {st.mean(x['margin'] for x in v):>10,.0f}")
        cc = Counter(x["tax"] for x in v)
        for t, m in cc.most_common():
            print(f"        {t:30s} {m:3d} ({100*m/len(v):4.1f}%)")
    print()
    print("--- herd-size histogram of real opponents ---")
    h = Counter()
    for r in rows:
        na = r["o"]["n_animals"]
        h[(na // 5) * 5] += 1
    for k in sorted(h):
        print(f"  {k:2d}-{k+4:2d} animals: {h[k]:3d}  {'#'*h[k]}")
    print()
    print("--- animal revenue share histogram ---")
    h2 = Counter()
    for r in rows:
        h2[int(r["opp_anim_share"] * 10) * 10] += 1
    for k in sorted(h2):
        print(f"  {k:3d}-{k+9:3d}%: {h2[k]:3d}  {'#'*h2[k]}")
    json.dump([{k: v for k, v in r.items() if k not in ("o", "u")} for r in rows],
              open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rows.json"), "w"), indent=1)
