import gzip, json, glob, sys, statistics as st
from collections import Counter, defaultdict
refs = json.load(open("runs/opening_pos_refs.json")); seqs = [s for runs in refs.values() for s in runs]
US = "misis biznessmenlb"
def cls(d, q):
    alive = list(range(len(seqs)))
    for t in range(1, 25):
        f = d["steps"][t][0]["observation"]["farms"][q]
        pos = [list(f["farmer"])] + [list(h) for h in (f.get("hands") or [])]
        alive = [i for i in alive if len(seqs[i]) > t - 1 and seqs[i][t - 1] == pos]
        if not alive: return "reactive"
    return "clone"
out = []
for sub in sys.argv[1:]:
    for f in sorted(glob.glob(f"replays/{sub}/*.gz")):
        d = json.load(gzip.open(f, "rt")); n = d["info"]["TeamNames"]; r = d["rewards"]
        if n[0] == n[1] or US not in n: continue
        p = n.index(US); q = 1 - p
        out.append(dict(sub=sub, file=f, seat=p, opp=n[q], res="W" if r[p] > r[q] else "D" if r[p] == r[q] else "L",
                        me=r[p], them=r[q], margin=r[p] - r[q], cls=cls(d, q)))
json.dump(out, open("runs/ladder_qAqB.json", "w"))
for sub in sys.argv[1:]:
    rows = [x for x in out if x["sub"] == sub]
    print(f"== {sub}: n={len(rows)}", dict(Counter(x["res"] for x in rows)))
    for c in ("clone", "reactive"):
        rr = [x for x in rows if x["cls"] == c]
        if not rr: continue
        L = [x for x in rr if x["res"] == "L"]
        print(f"   {c:9} {len(rr):3} games W/D/L {sum(x['res']=='W' for x in rr)}/{sum(x['res']=='D' for x in rr)}/{len(L)}  "
              f"our money med {st.median(x['me'] for x in rr):.0f} opp {st.median(x['them'] for x in rr):.0f}  "
              f"loss margin med {st.median([x['margin'] for x in L]) if L else 0:.0f}")
