"""Summarize only the predeclared complete paired T046 development worlds."""
import argparse
import json
from pathlib import Path
import numpy as np


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--run',required=True)
    a=ap.parse_args(); root=Path(a.run)
    manifest=json.loads((root/'resume_manifest.json').read_text())
    rows=[json.loads(x) for x in (root/'games.jsonl').read_text().splitlines() if x.strip()]
    used=[r for r in rows if r['seed'] in manifest['seeds']]
    expected={(s,o,p,v) for s in manifest['seeds'] for o in manifest['opponents'] for p in (0,1) for v in manifest['variants']}
    indexed={(r['seed'],r['opp'],r['seat'],r['variant']):r for r in used}
    assert len(indexed)==len(used), 'duplicate records'
    assert set(indexed)==expected, ('incomplete',len(indexed),len(expected))
    assert all(r.get('status')==['DONE','DONE'] and 'error' not in r and r['counts'].get('exceptions',0)==0 and r['counts']['calls']==719 for r in used)
    rng=np.random.default_rng(46000)
    ii=rng.integers(0,len(manifest['seeds']),size=(20000,len(manifest['seeds'])))
    def summary(rs):
        return dict(games=len(rs),wins=sum(r['score']==1 for r in rs),draws=sum(r['score']==.5 for r in rs),
                    losses=sum(r['score']==0 for r in rs),score=float(np.mean([r['score'] for r in rs])),
                    margin=float(np.mean([r['margin'] for r in rs])),
                    max_call=max(r['latency']['max'] for r in rs),
                    median_game_p50=float(np.median([r['latency']['p50'] for r in rs])),
                    seconds_mean=float(np.mean([r['seconds'] for r in rs])),
                    total_overage=sum(r['overage'] for r in rs))
    result=dict(seeds=manifest['seeds'],games=len(used),errors=0,excluded_outside_complete_plan=len(rows)-len(used),
                note='4-world development screen; interrupted for CPU resource contention, before inspecting scores; not a gate',variants={})
    for v in manifest['variants']:
        rs=[r for r in used if r['variant']==v]; result['variants'][v]=summary(rs)
        result['variants'][v]['by_opp']={o:summary([r for r in rs if r['opp']==o]) for o in manifest['opponents']}
        for h in ('op','target','market'):
            n=sum(r['counts'].get(h+'_n',0) for r in rs)
            if n:
                result['variants'][v][h+'_disagreement']=sum(r['counts'].get(h+'_disagree',0) for r in rs)/n
        if v=='baseline':
            continue
        ds=[];dm=[]
        for s in manifest['seeds']:
            pairs=[(indexed[s,o,p,v],indexed[s,o,p,'baseline']) for o in manifest['opponents'] for p in (0,1)]
            ds.append(float(np.mean([r['score']-b['score'] for r,b in pairs])))
            dm.append(float(np.mean([r['margin']-b['margin'] for r,b in pairs])))
        result['variants'][v]['paired']=dict(score=float(np.mean(ds)),margin=float(np.mean(dm)),world_score=ds,world_margin=dm,
            score_ci95=np.quantile(np.array(ds)[ii].mean(1),[.025,.975]).tolist(),
            margin_ci95=np.quantile(np.array(dm)[ii].mean(1),[.025,.975]).tolist())
    (root/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
