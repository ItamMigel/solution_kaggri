"""Our ladder record per submission from census_ours fp. usage: python ladder_ours.py"""
import json, collections, statistics as st
OURS = "misis biznessmenlb"
idx = {}
for l in open('/workspace/shared/replays/ours/index.jsonl'):
    d = json.loads(l); idx[d['episode_id']] = d['sub']
agg = collections.defaultdict(list)
for ep, sub in idx.items():
    try: d = json.load(open(f'/workspace/shared/research/census_ours/fp/{ep}.json'))
    except Exception: continue
    ps = [i for i in range(2) if d['names'][i] == OURS]
    if len(ps) != 1: continue
    p = ps[0]; me, op = d['players'][p], d['players'][1 - p]
    agg[sub].append((me['final'] - op['final'], op['name'], me, op, ep))
def herd(x): return "/".join(str(x['animals'].get(k, 0)) for k in ("COW", "SHEEP", "GOOSE"))
for sub, l in agg.items():
    w = sum(x[0] > 0 for x in l); dr = sum(x[0] == 0 for x in l)
    print(f"{sub:11s} n={len(l):3d} W-D-L={w}-{dr}-{len(l)-w-dr} mean={st.mean(x[0] for x in l):+7.0f} median={st.median(x[0] for x in l):+7.0f}")
    for m, n, me, op, ep in sorted(l, key=lambda x: x[0])[:5]:
        if m < 0: print(f"   {m:+7.0f} ep{ep} vs {n[:20]:20s} herd us {herd(me)} them {herd(op)} hands {max(me['hands_by_day'])}/{max(op['hands_by_day'])}")
