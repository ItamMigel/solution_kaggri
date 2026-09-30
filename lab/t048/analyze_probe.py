"""Summarize development trajectories; forecast inputs remain public-only."""
import collections
import gzip
import json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
OUT=Path('/workspace/shared/runs/t048_dev_probe')
engine={};exec((HERE/'market_engine.py').read_text(),engine)
PRODUCTS=('CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL')

def demand(record,item):
    t=record['step'];d=int(t%24==0)
    if t%4==0:
        for s in record['town']['unlocked_shops']:
            items=engine['SHOPS'][s]
            if item in items:d+=2 if len(items)==1 else 1
    return d

def main():
    games=[]; forecasts=[]; hist=collections.Counter(); errors=[]
    for path in sorted(OUT.glob('*_0.json.gz')):
        data=json.load(gzip.open(path,'rt'));rr=data['records'];counts=collections.Counter()
        for r in rr:
            orders=r['orders'][0]
            boundary=max((i for i,o in enumerate(orders) if o[0] not in ('SELL','NOOP')),default=-1)
            suffix=[o for o in orders[boundary+1:] if o[0]=='SELL']
            counts['multi_suffix_after14']+=int(r['step']>=336 and len(suffix)>=2)
            counts['late28_orders']+=int(r['step']>=672)*len(orders)
        for it in PRODUCTS:
            flow=[]
            for j,r in enumerate(rr):
                own=r['shed'][0][it]-r['shed_after'][0][it]
                observed=r['market_after']['inventory'][it]-r['market']['inventory'][it]-own
                valid=(r['market']['prices'][it]>10 and r['market_after']['prices'][it]>1)
                if valid:
                    actual=r['shed'][1][it]-r['shed_after'][1][it]
                    if observed!=actual:errors.append((path.name,r['step'],it,observed,actual))
                if j>=672 and j+4<len(rr) and len(flow)>=24 and all(x is not None for x in flow[-24:]):
                    history=flow[-24:]
                    predicted=np.mean([sum(history[k:k+4]) for k in range(21)])
                    future=rr[j:j+4]
                    actual=sum(x['shed'][1][it]-x['shed_after'][1][it] for x in future)
                    forecasts.append(dict(game=path.name,item=it,step=r['step'],predicted=float(predicted),actual=actual,
                                          known_town=sum(demand(x,it) for x in future),stock=r['shed'][0][it]))
                flow.append(max(0,observed) if valid else None)
        games.append(dict(game=path.name,status=data['status'],rewards=data['rewards'],**counts))
    report=dict(games=games,public_flow_mismatches=errors,forecast={})
    for it in PRODUCTS:
        rows=[x for x in forecasts if x['item']==it]
        if rows:
            report['forecast'][it]=dict(n=len(rows),predicted=float(np.mean([x['predicted'] for x in rows])),
                actual=float(np.mean([x['actual'] for x in rows])),mae=float(np.mean([abs(x['predicted']-x['actual']) for x in rows])),
                demand=float(np.mean([x['known_town'] for x in rows])))
    (OUT/'analysis.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
