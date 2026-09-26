"""Decision log: replay → per-step (state features, decisions) rows for one named team (reverse-engineering of top agents).
usage: python declog.py --team "Boey" --glob '/workspace/shared/replays/top10v4/*/*.gz' --out /workspace/shared/research/re/boey.jsonl.gz --workers 6"""
import argparse, glob, gzip, json, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

def load(f):
    return json.load(gzip.open(f, "rt")) if f.endswith(".gz") else json.load(open(f))

def farm_feats(farm):
    c = Counter(); ripe = Counter(); animals = Counter(); structs = Counter(); fert = 0
    for row in farm["tiles"]:
        for t in row:
            if not t: c["empty"] += 1; continue
            if isinstance(t, str): c[t.lower()] += 1; continue
            k = t.get("kind")
            if k == "PLANT":
                c["plant_" + t["crop"]] += 1; ripe[t["crop"]] += t.get("yield_units", 0)
                fert += t.get("fertilized_until_day", -1) >= 0
            elif k in ("PASTURE", "COOP"):
                structs[k] += 1
                if t.get("animal"): animals[t["animal"]] += 1
            else: c[k.lower()] += 1
    return dict(tiles=dict(c), ripe=dict(ripe), animals=dict(animals), structs=dict(structs), fert_tiles=fert,
                hands=len(farm["hands"]), quads=len(farm.get("unlocked_quadrants", [])), money=farm["money"], hires_today=farm.get("hires_today", 0))

def one(args):
    f, team = args
    try:
        d = load(f); names = d["info"].get("TeamNames", [])
        if team not in names: return []
        p = names.index(team); o = 1 - p; rows = []; T = len(d["steps"]) - 1
        for t in range(T):
            ob = d["steps"][t][p]["observation"]; sh = d["steps"][t][0]["observation"]
            farms = ob.get("farms") or sh["farms"]; mk = ob.get("market") or sh["market"]
            priv = ob.get("private") or {}
            a = d["steps"][t + 1][p].get("action") or {}
            units = [a.get("farmer")] + list(a.get("hands") or [])
            ops = Counter((u[0] if isinstance(u, list) and u else "NONE") for u in units)
            carried = Counter()
            for inv in priv.get("inventories", []):
                for k, v in inv.items(): carried[k] += v
            rows.append(dict(ep=os.path.basename(f)[8:17], opp=names[o], step=t, day=sh.get("day"), hour=sh.get("hour"),
                             me=farm_feats(farms[p]), op=farm_feats(farms[o]), shed=priv.get("shed", {}), seeds=priv.get("seeds", {}),
                             carried=dict(carried), prices=mk["prices"], inv=mk["inventory"], shops=(ob.get("town") or sh.get("town") or {}).get("unlocked_shops", []),
                             market=a.get("market") or [], ops=dict(ops), reward=d["rewards"][p], opp_reward=d["rewards"][o]))
        return rows
    except Exception as e:
        return [dict(error=repr(e), file=f)]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--team"); ap.add_argument("--glob"); ap.add_argument("--out"); ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(); fs = sorted(set(glob.glob(a.glob))); os.makedirs(os.path.dirname(a.out), exist_ok=True); n = err = 0
    with ProcessPoolExecutor(a.workers) as ex, gzip.open(a.out, "wt") as w:
        for rows in ex.map(one, [(f, a.team) for f in fs], chunksize=4):
            for r in rows:
                if "error" in r: err += 1; continue
                w.write(json.dumps(r) + "\n"); n += 1
    print(a.team, "rows", n, "errors", err)
