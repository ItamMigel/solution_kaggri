"""Interpretable rule extraction (decision trees) for macro decisions of a team from its decision log.
usage: python rules.py dsm mmpq   → research/re/rules_<tags>.md"""
import gzip, json, sys, random
import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text
R = "/workspace/shared/research/re"; ITEMS = ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER"]
def feats(r):
    m, o = r["me"], r["op"]; f = {"day": r["day"], "hour": r["hour"], "money": m["money"], "quads": m["quads"], "hands": m["hands"],
         "hires_today": m["hires_today"], "opp_money": o["money"], "opp_quads": o["quads"], "n_shops": len(r["shops"]), "fert_tiles": m["fert_tiles"]}
    for a in ("COW","SHEEP","GOOSE"): f["n_"+a] = m["animals"].get(a, 0)
    for s in ("PASTURE","COOP"): f["st_"+s] = m["structs"].get(s, 0)
    for c in ("WHEAT","CARROT","TOMATO","STRAWBERRY","MELON"): f["tile_"+c] = m["tiles"].get("plant_"+c, 0); f["ripe_"+c] = m["ripe"].get(c, 0)
    f["empty"] = m["tiles"].get("empty", 0)
    for i in ITEMS: f["shed_"+i] = r["shed"].get(i, 0) + r["carried"].get(i, 0); f["price_"+i] = r["prices"][i]; f["inv_"+i] = r["inv"][i]
    for i in ("GOOSE","COW","SHEEP"): f["shed_"+i] = r["shed"].get(i, 0)
    for c in ("WHEAT","CARROT","TOMATO","STRAWBERRY","MELON"): f["seed_"+c] = r["seeds"].get(c, 0)
    return f
def targets(r):
    t = {"BUY_LAND": 0, "HIRE": 0}
    for o in r["market"]:
        if not o: continue
        op = o[0]; it = o[1] if len(o) > 1 else ""; q = o[2] if len(o) > 2 and isinstance(o[2], (int, float)) else 1
        if op in ("BUY_LAND", "HIRE"): t[op] += 1
        elif op in ("SELL", "BUY_ANIMAL", "BUY_SEED", "BUY_PRODUCT"): t[op + "_" + it] = t.get(op + "_" + it, 0) + q
    return t
tags = sys.argv[1:]; rows = []
for tag in tags: rows += [json.loads(l) for l in gzip.open(f"{R}/{tag}.jsonl.gz", "rt")]
eps = sorted({r["ep"] for r in rows}); random.Random(0).shuffle(eps); test = set(eps[: len(eps) // 4])
F = [feats(r) for r in rows]; names = list(F[0]); X = np.array([[f[k] for k in names] for f in F], float)
T = [targets(r) for r in rows]; te = np.array([r["ep"] in test for r in rows])
out = [f"# Rules for {'+'.join(tags)} ({len(eps)} episodes, {len(rows)} steps; test = 25% held-out episodes)\n"]
for tgt in ["BUY_LAND", "HIRE", "BUY_ANIMAL_GOOSE", "BUY_ANIMAL_COW", "BUY_ANIMAL_SHEEP", "SELL_EGG", "SELL_WHEAT", "BUY_PRODUCT_WHEAT", "SELL_STRAWBERRY", "SELL_MILK", "SELL_WOOL", "SELL_MELON", "BUY_SEED_WHEAT", "BUY_SEED_STRAWBERRY"]:
    y = np.array([min(t.get(tgt, 0), 3) if tgt in ("HIRE",) else int(t.get(tgt, 0) > 0) for t in T])
    if y.sum() < 20: continue
    clf = DecisionTreeClassifier(max_depth=4, min_samples_leaf=40, class_weight="balanced", random_state=0).fit(X[~te], y[~te])
    p = clf.predict(X[te]); pos = y[te] > 0
    rec = (p[pos] == y[te][pos]).mean() if pos.any() else float("nan"); prec = (y[te][p > 0] > 0).mean() if (p > 0).any() else float("nan")
    out.append(f"## {tgt}: positives {int((y>0).sum())}; held-out acc {(p==y[te]).mean():.3f}, recall(pos) {rec:.2f}, precision {prec:.2f}\n```\n{export_text(clf, feature_names=names, max_depth=4)}```\n")
open(f"{R}/rules_{'_'.join(tags)}.md", "w").write("\n".join(out)); print("\n".join(o.split('\n')[0] for o in out))
