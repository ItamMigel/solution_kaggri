"""Inverse estimation of a top team's task valuation (conditional logit over trips).
Trip = a unit's path from its previous productive op to the next one; choice set = all tasks available at trip start.
usage: python task_logit.py "M & M & P & Q" '/workspace/shared/replays/top10v4/mmpq/*.gz' 40 out.json"""
import glob, gzip, json, sys, random, math
import numpy as np
OPS = ["WATER", "HARVEST_P", "HARVEST_A", "FEED", "CARE", "COLLECT_FERTILIZER", "PLANT", "DIG", "BUILD", "PLACE", "FERTILIZE"]
CROPS = {"WHEAT": (2, 4, False, 6), "CARROT": (2, 3, False, 4), "TOMATO": (8, 8, True, 4), "STRAWBERRY": (10, 10, True, 4), "MELON": (10, 12, False, 6)}
MOVES = {"NORTH", "SOUTH", "EAST", "WEST", "PASS", "PICKUP", "DROP"}
def feats_for(op, tile, day, hour, dist, carrying_w):
    f = np.zeros(len(OPS) + 8); f[OPS.index(op)] = 1; k = len(OPS)
    f[k] = dist; f[k + 1] = math.log1p(dist)
    if tile and isinstance(tile, dict):
        f[k + 2] = tile.get("consecutive_unwatered", 0) if op == "WATER" else 0
        f[k + 3] = tile.get("consecutive_unfed", 0) if op == "FEED" else 0
        f[k + 4] = tile.get("yield_units", 0) if op.startswith("HARVEST") else 0
    f[k + 5] = hour / 23.0; f[k + 6] = (op == "FEED") * (1 - carrying_w); f[k + 7] = (op == "WATER") * (hour / 23.0)
    return f
NAMES = OPS + ["dist", "log1p_dist", "unwatered", "unfed", "yield", "hour", "feed_needs_fetch", "water_x_hour"]
def candidates(tiles, day):
    out = []
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if t is None: out.append(("PLANT", (x, y), None)); out.append(("BUILD", (x, y), None)); continue
            if not isinstance(t, dict): continue
            k = t.get("kind")
            if k == "WEED": out.append(("DIG", (x, y), t)); continue
            if k == "PLANT":
                if not t.get("watered_today"): out.append(("WATER", (x, y), t))
                fyd, myd, ong, mx = CROPS[t["crop"]]
                if t.get("yield_units", 0) > 0 and (ong or day - t["planted_day"] >= fyd): out.append(("HARVEST_P", (x, y), t))
                out.append(("FERTILIZE", (x, y), t))
            elif t.get("animal"):
                if not t.get("fed_today"): out.append(("FEED", (x, y), t))
                if not t.get("cared_today"): out.append(("CARE", (x, y), t))
                if t.get("yield_units", 0) > 0: out.append(("HARVEST_A", (x, y), t))
                if t.get("fertilizer_available"): out.append(("COLLECT_FERTILIZER", (x, y), t))
            elif k in ("COOP", "PASTURE"): out.append(("PLACE", (x, y), t))
    return out
def canon(op, tile):
    if op == "HARVEST": return "HARVEST_A" if isinstance(tile, dict) and tile.get("animal") else "HARVEST_P"
    if op in ("BUILD_COOP", "BUILD_PASTURE"): return "BUILD"
    return op
def trips(path, team, max_cands=150):
    d = json.load(gzip.open(path, "rt")); names = d["info"]["TeamNames"]
    if team not in names: return []
    p = names.index(team); rows = []; start = {}
    for t in range(1, len(d["steps"]) - 1):
        ob = d["steps"][t][p]["observation"]; sh = d["steps"][t][0]["observation"]
        farm = (ob.get("farms") or sh["farms"])[p]; day = sh["day"]; hour = sh["hour"]
        units = [tuple(farm["farmer"])] + [tuple(h) for h in farm["hands"]]
        act = d["steps"][t + 1][p].get("action") or {}; ua = [act.get("farmer")] + list(act.get("hands") or [])
        invs = (ob.get("private") or {}).get("inventories") or []
        for i, u in enumerate(units):
            a = ua[i] if i < len(ua) else None; op = a[0] if isinstance(a, list) and a else "PASS"
            if (hour == 0 and i > 0) or i not in start: start[i] = (t, u, farm["tiles"], day, hour, invs[i] if i < len(invs) else {})
            if op in MOVES: continue
            tile = farm["tiles"][u[1]][u[0]]; c = canon(op, tile)
            if c not in OPS: start[i] = (t, u, farm["tiles"], day, hour, {}); continue
            t0, u0, tiles0, d0, h0, inv0 = start[i]
            cands = candidates(tiles0, d0)
            chosen = next((j for j, (o, xy, _) in enumerate(cands) if o == c and xy == u), None)
            if chosen is not None and len(cands) > 1:
                if len(cands) > max_cands:
                    keep = [chosen] + random.sample([j for j in range(len(cands)) if j != chosen], max_cands - 1); cands = [cands[j] for j in keep]; chosen = 0
                cw = 1 if inv0.get("WHEAT", 0) > 0 else 0
                X = np.array([feats_for(o, tt, d0, h0, abs(u0[0] - xy[0]) + abs(u0[1] - xy[1]), cw) for o, xy, tt in cands])
                rows.append((X, chosen))
            start[i] = (t, u, farm["tiles"], day, hour, {})
    return rows
def fit(rows, iters=300, lr=0.05, l2=1e-3):
    w = np.zeros(rows[0][0].shape[1])
    for it in range(iters):
        g = np.zeros_like(w); ll = 0
        for X, c in rows:
            s = X @ w; s -= s.max(); p = np.exp(s); p /= p.sum(); g += X[c] - p @ X; ll += math.log(p[c] + 1e-12)
        w += lr * (g / len(rows) - l2 * w)
        if it % 50 == 0: print(it, "avg LL %.3f" % (ll / len(rows)), flush=True)
    return w
def top1(rows, w):
    return np.mean([int(np.argmax(X @ w) == c) for X, c in rows])
if __name__ == "__main__":
    team, pat, n, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    fs = sorted(glob.glob(pat)); random.Random(1).shuffle(fs); rows = []; test = []
    for k, f in enumerate(fs[:n]):
        r = trips(f, team); (test if k % 5 == 0 else rows).extend(r)
    print("train trips", len(rows), "test trips", len(test), flush=True)
    w = fit(rows)
    res = {"names": NAMES, "w": w.tolist(), "train_top1": float(top1(rows, w)), "test_top1": float(top1(test, w)),
           "chance": float(np.mean([1 / len(X) for X, _ in test]))}
    json.dump(res, open(out, "w"), indent=1); print(json.dumps({k: res[k] for k in ("train_top1", "test_top1", "chance")}))
    for nm, v in sorted(zip(NAMES, w), key=lambda x: -abs(x[1])): print(f"{nm:22s} {v:+.3f}")
