"""Economy comparison across teams: exact trades (trades_*.jsonl.gz) + decision logs (<team>.jsonl.gz)."""
import json, gzip, sys
from collections import defaultdict
R = "/workspace/shared/research/re"
def trades(tag):
    G = [json.loads(l) for l in gzip.open(f"{R}/trades_{tag}.jsonl.gz", "rt")]; n = len(G); agg = defaultdict(float); units = defaultdict(float); win = 0; money = 0
    for g in G:
        me = g["me"]; win += g["rewards"][me] > g["rewards"][1 - me]; money += g["rewards"][me]
        for pid, step, op, item, price, inv in g["trades"]:
            if pid != me: continue
            sgn = 1 if op == "SELL" else -1; agg[(op if op != "SELL" else "SELL", item)] += sgn * price; units[(op, item)] += 1
    return n, win / max(1, n), money / max(1, n), {k: v / n for k, v in agg.items()}, {k: v / n for k, v in units.items()}
def timeline(tag):
    tl = defaultdict(lambda: defaultdict(list))
    for l in gzip.open(f"{R}/{tag}.jsonl.gz", "rt"):
        r = json.loads(l)
        if r["hour"] != 2: continue
        m = r["me"]; d = r["day"]
        tl[d]["quads"].append(m["quads"]); tl[d]["hands"].append(m["hands"]); tl[d]["money"].append(m["money"])
        for a in ("COW", "SHEEP", "GOOSE"): tl[d][a].append(m["animals"].get(a, 0))
        for c in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"): tl[d][c].append(m["tiles"].get("plant_" + c, 0))
    return {d: {k: sum(v) / len(v) for k, v in x.items()} for d, x in tl.items()}
if __name__ == "__main__":
    tags = sys.argv[1:]
    res = {t: trades(t) for t in tags}
    print("games/win/money:", {t: (r[0], round(r[1], 2), round(r[2])) for t, r in res.items()})
    keys = sorted({k for r in res.values() for k in r[3]}, key=lambda k: -abs(res[tags[0]][3].get(k, 0)))
    print(f"{'net $/game':28s}" + "".join(f"{t:>12s}" for t in tags))
    for k in keys: print(f"{k[0][:12]+' '+k[1]:28s}" + "".join(f"{res[t][3].get(k, 0):12.0f}" for t in tags))
