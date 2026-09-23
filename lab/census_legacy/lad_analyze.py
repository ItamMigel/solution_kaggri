"""Classify the opponents we actually faced on the kaggriculture ladder."""
import csv, json, glob, os, sys
from collections import Counter, defaultdict

FP = "/workspace/kaggriculture/replays_mine/fp"
LOCAL = "/tmp/claude-0/-workspace/dc512510-85c8-45da-adba-d688751dd8b1/scratchpad/fp_local"
US = "Adil Khabibullin"

SUBS = {
    "55203378": ("exp029/cand_f4", 1132.1),
    "55202902": ("exp028", 1111.7),
    "55201960": ("exp027", 900.4),
    "55174946": ("exp023b", 830.9),
    "55173278": ("exp025", 887.0),
    "55173274": ("exp022", 914.2),
}


def ep2sub():
    m = {}
    for f in glob.glob("/workspace/kaggriculture/replays_mine/meta/eps_*.csv"):
        sub = os.path.basename(f)[4:-4]
        for row in csv.DictReader(open(f)):
            m.setdefault(row["id"], []).append(sub)
    return m


def lb_scores():
    d = {}
    for row in csv.DictReader(open("/tmp/claude-0/-workspace/dc512510-85c8-45da-adba-d688751dd8b1/scratchpad/lb_full.csv")):
        d[row["teamName"]] = float(row["score"])
    return d


def classify(r):
    h = r["herd"]; na = r["n_animals"]
    s = r["sells"]; sd = r["seeds"]
    straw = s.get("STRAWBERRY", 0); mel = s.get("MELON", 0)
    milk = s.get("MILK", 0); wool = s.get("WOOL", 0)
    tot = sum(s.values())
    unit_ops = sum(r["unit_ops"].values())

    if unit_ops < 200 or tot < 25:
        return "INACTIVE/BROKEN"
    fs = 0
    if 6 <= h["COW"] <= 10 and 3 <= h["SHEEP"] <= 8 and h["GOOSE"] == 0: fs += 1
    if r["n_quad"] == 3: fs += 1
    if 11 <= r["hands"] <= 13: fs += 1
    if straw >= 180: fs += 1
    if r["products_bought"].get("WHEAT", 0) >= 500: fs += 1
    if 30 <= sd.get("STRAWBERRY", 0) <= 60 and 12 <= sd.get("MELON", 0) <= 32: fs += 1
    if fs >= 5: return "FRONTIER"
    if fs == 4: return "FRONTIER-LIKE"
    if na == 0: return "CROP-ONLY"
    if na >= 15: return "ANIMAL-HEAVY"
    if (milk + wool) > 1.4 * max(1, straw + mel): return "ANIMAL-LED"
    if na >= 3: return "MIXED"
    return "OTHER"


def build():
    e2s = ep2sub(); lb = lb_scores()
    rows = []
    for f in sorted(glob.glob(FP + "/*.json")):
        recs = json.load(open(f))
        ep = os.path.basename(f)[:-5]
        if not ep.isdigit():
            continue
        us = [r for r in recs if r["name"] == US]
        opp = [r for r in recs if r["name"] != US]
        if len(us) != 1 or len(opp) != 1:
            continue
        u, o = us[0], opp[0]
        subs = e2s.get(str(ep), [])
        rows.append({
            "ep": ep, "sub": subs[0] if subs else "?",
            "our_money": u["money"], "opp_money": o["money"],
            "margin": u["money"] - o["money"],
            "win": u["money"] > o["money"],
            "opp": o["name"], "opp_lb": lb.get(o["name"]),
            "cls": classify(o), "o": o, "u": u,
        })
    return rows


def fmt_fp(r):
    h = r["herd"]
    s = {k: v for k, v in sorted(r["sells"].items(), key=lambda kv: -kv[1])}
    return (f"{h['COW']}c/{h['SHEEP']}s/{h['GOOSE']}g h{r['hands']} q{r['n_quad']} "
            f"seed={r['seeds']} bp={r['products_bought']} sold={s}")


if __name__ == "__main__":
    rows = build()
    print(f"=== {len(rows)} ladder episodes ===")
    c = Counter(r["cls"] for r in rows)
    for k, v in c.most_common():
        print(f"  {k:18s} {v:4d}  {100*v/len(rows):5.1f}%")
