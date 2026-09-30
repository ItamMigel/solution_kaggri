"""Predeclared whole-world inference, with paired external-opponent controls."""
import argparse
import json
from pathlib import Path
import numpy as np

def ci(values):
    a=np.asarray(values,dtype=float)
    if not len(a):return None
    rng=np.random.default_rng(48020260930)
    samples=a[rng.integers(len(a),size=(100000,len(a)))].mean(1)
    return list(map(float,np.quantile(samples,[.025,.975])))

def group(rows):
    valid=[r for r in rows if r['valid']]
    worlds=[rr for s in sorted({r['seed'] for r in valid})
            if len(rr:=[r for r in valid if r['seed']==s])==2 and {r['seat'] for r in rr}=={0,1}]
    margins=[float(np.mean([r['margin'] for r in rr])) for rr in worlds]
    points=[float(np.mean([r['points'] for r in rr])) for rr in worlds]
    return dict(n=len(rows),valid=len(valid),worlds=len(worlds),world_margins=margins,
                points=sum(r['points'] for r in valid),wins=sum(r['margin']>0 for r in valid),
                draws=sum(r['margin']==0 for r in valid),losses=sum(r['margin']<0 for r in valid),
                mean_margin=float(np.mean([r['margin'] for r in valid])) if valid else None,
                margin_world95=ci(margins),points_world95=ci(points))

def summarize(out):
    mf=json.loads((out/'manifest.json').read_text())
    rows=[json.loads(x) for x in (out/'games.jsonl').read_text().splitlines()]
    expected={tuple(j) for j in mf['jobs']}
    keys=[(r['variant'],r['opp'],r['seed'],r['seat']) for r in rows]
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    result=dict(records=len(rows),expected=len(expected),complete=set(keys)==expected,
                errors=sum(not r['valid'] for r in rows),variants={},control={})
    for opp in ('tetsu','ozer44'):
        result['control'][opp]=group([r for r in rows if r['variant']=='base' and r['opp']==opp])
    for variant in ('sale_beam','late_ev'):
        rrv=[r for r in rows if r['variant']==variant]
        groups={o:group([r for r in rrv if r['opp']==o]) for o in ('base','tetsu','ozer44')}
        sanity_pass=True
        for opp in ('tetsu','ozer44'):
            baseline={(r['seed'],r['seat']):r for r in rows if r['variant']=='base' and r['opp']==opp and r['valid']}
            pairs=[(r,baseline[(r['seed'],r['seat'])]) for r in rrv
                   if r['opp']==opp and r['valid'] and (r['seed'],r['seat']) in baseline]
            whole=[[(r,b) for r,b in pairs if r['seed']==s] for s in sorted({r['seed'] for r,b in pairs})]
            whole=[rr for rr in whole if len(rr)==2]
            ds=[np.mean([r['points']-b['points'] for r,b in rr]) for rr in whole]
            dm=[np.mean([r['margin']-b['margin'] for r,b in rr]) for rr in whole]
            groups[opp]['paired_control']=dict(n=len(pairs),worlds=len(whole),delta_points=sum(r['points']-b['points'] for r,b in pairs),
                delta_score=float(np.mean(ds)) if ds else None,score_world95=ci(ds),
                delta_margin=float(np.mean(dm)) if dm else None,margin_world95=ci(dm))
            g=groups[opp];p=g['paired_control']
            sanity_pass &= (g['n']==g['valid']==16 and p['n']==16 and p['worlds']==8
                            and p['delta_points']>=0 and p['delta_margin']>=0)
        h=groups['base']
        h2h_pass=(h['n']==h['valid']==32 and h['worlds']==16 and h['points']/32>=.65
                  and h['margin_world95'][0]>0)
        stats=[r['telemetry'][r['seat']]['t048'] for r in rrv if r['valid']]
        result['variants'][variant]=dict(opponents=groups,h2h_pass=bool(h2h_pass),sanity_pass=bool(sanity_pass),
            passed=bool(result['complete'] and not result['errors'] and h2h_pass and sanity_pass),
            telemetry={k:sum(float(s.get(k,0)) for s in stats) for k in ('errors','changed','searched','scored','added','held','released','expected_gain')},
            max_call=max((r['latency'][r['seat']]['max'] for r in rrv if r['valid']),default=None),
            overage=sum(r['latency'][r['seat']]['overage'] for r in rrv if r['valid']))
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path('/workspace/shared/runs/t048_ev_gate'))
    a=ap.parse_args();print(json.dumps(summarize(a.out),indent=2))
