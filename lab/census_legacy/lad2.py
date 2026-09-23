"""Re-measure the ladder field: OLD corpus (mined 2026-08-03, subs exp022..exp029) vs
NEW corpus (mined 2026-08-04, subs exp030/031/032/033).

Reuses the 2026-08-03 taxonomy verbatim (taxo.taxon + report.variant) so the two censuses
are directly comparable, then adds:
  * side-by-side archetype shares
  * per-archetype fingerprint means (money AND physical production) old vs new
  * unknown-cluster dump so a NEW archetype cannot hide inside "OTHER MIXED"
"""
import csv, glob, json, os, statistics as st, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/workspace/kaggriculture")
from taxo import taxon  # noqa: E402
from report import variant, anim_share  # noqa: E402

FP = "/workspace/kaggriculture/replays_mine/fp"
META = "/workspace/kaggriculture/replays_mine/meta"
US = "Adil Khabibullin"

OLD_SUBS = {"55203378": "exp029", "55202902": "exp028", "55201960": "exp027",
            "55174946": "exp023b", "55173278": "exp025", "55173274": "exp022"}
NEW_SUBS = {"55211073": "exp030", "55217743": "exp031", "55238393": "exp032",
            "55244472": "exp033"}
KEYS = ["STRAWBERRY", "MELON", "MILK", "WOOL", "FERTILIZER", "WHEAT", "CARROT"]


def ep_index():
    """episode id -> (sub, createTime)"""
    m = {}
    for f in glob.glob(META + "/eps_*.csv"):
        sub = os.path.basename(f)[4:-4]
        for row in csv.DictReader(open(f)):
            if row.get("id", "").isdigit():
                m[row["id"]] = (sub, row["createTime"])
    return m


def lb_scores(path):
    d = {}
    for row in csv.DictReader(open(path)):
        try:
            d[row["teamName"]] = float(row["score"])
        except (ValueError, KeyError):
            pass
    return d


def build():
    idx = ep_index()
    lb_new = lb_scores(os.path.join(HERE, "lb_full_new.csv"))
    lb_old = lb_scores(os.path.join(HERE, "lb_full.csv"))
    rows = []
    for f in sorted(glob.glob(FP + "/*.json")):
        ep = os.path.basename(f)[:-5]
        if not ep.isdigit():
            continue
        recs = json.load(open(f))
        us = [r for r in recs if r["name"] == US]
        opp = [r for r in recs if r["name"] != US]
        if len(us) != 1 or len(opp) != 1:
            continue
        u, o = us[0], opp[0]
        sub, t = idx.get(ep, ("?", "?"))
        era = "NEW" if sub in NEW_SUBS else ("OLD" if sub in OLD_SUBS else "?")
        rows.append({"ep": ep, "sub": sub, "era": era, "t": t,
                     "subname": NEW_SUBS.get(sub) or OLD_SUBS.get(sub) or "?",
                     "our_money": u["money"], "opp_money": o["money"],
                     "margin": u["money"] - o["money"], "win": u["money"] > o["money"],
                     "opp": o["name"],
                     "opp_lb": (lb_new if era == "NEW" else lb_old).get(o["name"]),
                     "o": o, "u": u})
    return rows


def label(r):
    t = taxon(r["o"])
    return variant(r["o"]) if t == "NOTEBOOK-FRONTIER FAMILY" else t


def prod_profile(recs):
    """mean money + physical production of a set of opponent fingerprints"""
    if not recs:
        return None
    g = lambda fn: st.mean(fn(x) for x in recs)  # noqa: E731
    return {
        "n": len(recs), "teams": len({x["name"] for x in recs}),
        "money": g(lambda x: x["money"]),
        "cow": g(lambda x: x["herd"]["COW"]), "sheep": g(lambda x: x["herd"]["SHEEP"]),
        "hands": g(lambda x: x["hands"]), "quad": g(lambda x: x["n_quad"]),
        "seeds": {k: g(lambda x, k=k: x["seeds"].get(k, 0)) for k in ("STRAWBERRY", "MELON", "WHEAT", "CARROT")},
        "sells": {k: g(lambda x, k=k: x["sells"].get(k, 0)) for k in KEYS},
        "bpWHEAT": g(lambda x: x["products_bought"].get("WHEAT", 0)),
        "rev": g(lambda x: x["revenue"]),
    }


def fmt_profile(p):
    if not p:
        return "  (none)"
    s = (f"  n={p['n']:3d} teams={p['teams']:3d}  money=${p['money']:>8,.0f}  "
         f"herd {p['cow']:.1f}c/{p['sheep']:.1f}s hands {p['hands']:.1f} quad {p['quad']:.2f}\n"
         f"    seeds " + " ".join(f"{k[:5]}={v:5.1f}" for k, v in p["seeds"].items()) +
         f"  bpWHEAT={p['bpWHEAT']:.0f}\n"
         f"    sold  " + " ".join(f"{k[:5]}={v:6.1f}" for k, v in p["sells"].items()))
    return s


def census(rows, title):
    n = len(rows)
    print(f"\n=== {title}: {n} episodes, {len({r['opp'] for r in rows})} distinct opponent teams ===")
    g = defaultdict(list)
    for r in rows:
        g[label(r)].append(r)
    print(f"  {'class':32s} {'n':>4s} {'share':>7s} {'teams':>6s} {'W-L':>9s} {'win%':>5s} {'mean margin':>12s} {'opp money':>10s}")
    for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])):
        w = sum(1 for x in v if x["win"])
        print(f"  {k:32s} {len(v):4d} {100*len(v)/n:6.1f}% {len({x['opp'] for x in v}):6d} "
              f"{w:3d}-{len(v)-w:<4d} {100*w/len(v):4.0f}% {st.mean(x['margin'] for x in v):12,.0f} "
              f"{st.mean(x['opp_money'] for x in v):10,.0f}")
    return g


if __name__ == "__main__":
    rows = build()
    old = [r for r in rows if r["era"] == "OLD"]
    new = [r for r in rows if r["era"] == "NEW"]
    print(f"TOTAL fingerprinted episodes: {len(rows)}  (OLD {len(old)}, NEW {len(new)}, unknown {len(rows)-len(old)-len(new)})")
    if new:
        ts = sorted(r["t"] for r in new)
        print(f"NEW window: {ts[0]}  ..  {ts[-1]}")
        print("NEW by submission:", dict(Counter(r["subname"] for r in new)))
    if old:
        ts = sorted(r["t"] for r in old)
        print(f"OLD window: {ts[0]}  ..  {ts[-1]}")

    go = census(old, "OLD corpus (2026-08-02..03)")
    gn = census(new, "NEW corpus (2026-08-03..04)")

    print("\n\n########## SHARE SHIFT ##########")
    keys = sorted(set(go) | set(gn), key=lambda k: -len(gn.get(k, [])))
    print(f"  {'class':32s} {'OLD n':>6s} {'OLD %':>7s} {'NEW n':>6s} {'NEW %':>7s} {'delta pp':>9s}")
    for k in keys:
        a, b = len(go.get(k, [])), len(gn.get(k, []))
        pa = 100 * a / max(1, len(old)); pb = 100 * b / max(1, len(new))
        print(f"  {k:32s} {a:6d} {pa:6.1f}% {b:6d} {pb:6.1f}% {pb-pa:+8.1f}")

    print("\n\n########## PER-ARCHETYPE STRENGTH: OLD vs NEW (money AND production) ##########")
    for k in keys:
        po = prod_profile([r["o"] for r in go.get(k, [])])
        pn = prod_profile([r["o"] for r in gn.get(k, [])])
        print(f"\n--- {k} ---")
        print(" OLD"); print(fmt_profile(po))
        print(" NEW"); print(fmt_profile(pn))
        if po and pn:
            print(f"    money {pn['money']/po['money']*100:5.1f}% of old   "
                  + "  ".join(f"{kk[:5]}={pn['sells'][kk]/max(1e-9,po['sells'][kk])*100:5.0f}%"
                              for kk in KEYS if po["sells"][kk] >= 20))

    print("\n\n########## NEW-CORPUS OPPONENTS NOT IN THE NOTEBOOK FAMILY (hunt for new archetypes) ##########")
    fam = ("NB-v1", "NB-v2", "NB-part")
    odd = [r for r in new if not label(r).startswith(fam)]
    odd.sort(key=lambda r: -r["opp_money"])
    print(f"  {len(odd)} of {len(new)} episodes ({100*len(odd)/max(1,len(new)):.1f}%)")
    for r in odd:
        o = r["o"]
        print(f"  ${o['money']:>8,.0f} {label(r):26s} {r['opp'][:22]:22s} lb={r['opp_lb'] or 0:6.0f} "
              f"h={o['herd']['COW']}c/{o['herd']['SHEEP']}s hands={o['hands']} q={o['n_quad']} "
              f"bpW={o['products_bought'].get('WHEAT',0)} seeds={ {k:v for k,v in o['seeds'].items()} } "
              f"sold={ {k:v for k,v in sorted(o['sells'].items(), key=lambda kv:-kv[1])[:5]} }")

    print("\n\n########## TOP-MONEY OPPONENTS IN THE NEW CORPUS ##########")
    top = sorted(new, key=lambda r: -r["opp_money"])[:20]
    for r in top:
        o = r["o"]
        print(f"  ${o['money']:>8,.0f} margin {r['margin']:>+9,.0f} {label(r):26s} {r['opp'][:20]:20s} "
              f"lb={r['opp_lb'] or 0:6.0f} h={o['herd']['COW']}c/{o['herd']['SHEEP']}s hands={o['hands']} "
              f"bpW={o['products_bought'].get('WHEAT',0)} sold={ {k:v for k,v in sorted(o['sells'].items(), key=lambda kv:-kv[1])[:5]} }")

    print("\n\n########## OUR RECORD BY SUBMISSION (new corpus) ##########")
    for s in sorted({r["subname"] for r in new}):
        v = [r for r in new if r["subname"] == s]
        w = sum(1 for x in v if x["win"])
        print(f"  {s}: {len(v):3d} eps {w}-{len(v)-w} ({100*w/len(v):.0f}%) mean margin {st.mean(x['margin'] for x in v):>10,.0f} "
              f"our money ${st.mean(x['our_money'] for x in v):>8,.0f} opp ${st.mean(x['opp_money'] for x in v):>8,.0f}")

    json.dump([{k: v for k, v in r.items() if k not in ("o", "u")} for r in rows],
              open(os.path.join(HERE, "rows2.json"), "w"), indent=1)
