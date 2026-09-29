"""Paired bootstrap over whole worlds; frozen-opponent suite conditional inference."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

FAMILIES={'tetsu':['tetsu','qA'],'v44':['ozer44','yaxon5','jaxa2802'], 'parthenos':['parthenos'], 'bc':['bc_m15ens','bc_mix4']}


def score(m):return float(m>0)+.5*float(m==0)


def summary(rows,base,variant):
    lookup={(r['variant'],r['opp'],r['seed'],r['seat']):r for r in rows if r['base']==base and r['valid']}
    pairs=[]
    for (v,o,s,p),r in lookup.items():
        if v!='off':continue
        b=r['rewards'][p]-r['rewards'][1-p]
        if variant=='terminal':
            rew=r['terminal']['rewards']
            delta=float(r['terminal']['changed'])
        else:
            rr=lookup.get((variant,o,s,p))
            if rr is None:continue
            rew=rr['rewards'];delta=rr['counts'].get('fix_changed_turns',0)
        m=rew[p]-rew[1-p]
        pairs.append(dict(opp=o,seed=s,seat=p,base=b,margin=m,delta_margin=m-b,
                          delta_score=score(m)-score(b),score=score(m),changed=delta))
    def stats(pp):
        worlds=defaultdict(list)
        for x in pp:worlds[x['seed']].append(x)
        if not pp:return {}
        vals=np.array([[np.mean([x[k] for x in w]) for k in ('delta_score','delta_margin')] for w in worlds.values()])
        rng=np.random.default_rng(450929)
        boot=vals[rng.integers(0,len(vals),(20000,len(vals)))].mean(axis=1)
        return dict(games=len(pp),worlds=len(worlds),games_per_world=sorted(set(map(len,worlds.values()))),
                    wins=sum(x['margin']>0 for x in pp),draws=sum(x['margin']==0 for x in pp),losses=sum(x['margin']<0 for x in pp),
                    baseline_score=float(np.mean([score(x['base']) for x in pp])),score=float(np.mean([x['score'] for x in pp])),
                    mean_margin=float(np.mean([x['margin'] for x in pp])),delta_score=float(vals[:,0].mean()),
                    delta_score_ci95=np.quantile(boot[:,0],[.025,.975]).tolist(),delta_margin=float(vals[:,1].mean()),
                    delta_margin_ci95=np.quantile(boot[:,1],[.025,.975]).tolist(),changed_games=sum(x['changed']>0 for x in pp),
                    changed_turns=sum(x['changed'] for x in pp),win_flips=sum(x['delta_score']>0 for x in pp),
                    loss_flips=sum(x['delta_score']<0 for x in pp))
    result=stats(pairs)
    if not result:return {}
    result['evaluation_methods'] = ({'exact_terminal_branch':len(pairs)} if variant=='terminal' else
                                    dict(Counter(lookup[variant,x['opp'],x['seed'],x['seat']].get('evaluation','full_game') for x in pairs)))
    result['opponents']={o:stats([x for x in pairs if x['opp']==o]) for o in sorted({x['opp'] for x in pairs})}
    result['without_own_mirror']=stats([x for x in pairs if x['opp'] != 'bc_'+base])
    result['full_games_without_action_changes']=(0 if variant=='terminal' else sum(lookup[variant,x['opp'],x['seed'],x['seat']].get('evaluation','full_game')=='full_game' and x['changed']==0 for x in pairs))
    result['families']={f:stats([x for x in pairs if x['opp'] in ops]) for f,ops in FAMILIES.items()}
    result['positive_score_ci']=result['delta_score_ci95'][0]>0
    result['family_ni_minus3pp']=all(v and v['delta_score_ci95'][0]>=-.03 for v in result['families'].values())
    result['recommendation_gate']=result['positive_score_ci'] and result['family_ni_minus3pp']
    result['note']='Conditional on frozen suite. Empirical bootstrap [0,0] from no flips is not proof of universal equivalence. Independent review required.'
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('run');a=ap.parse_args();root=Path(a.run)
    rows=[json.loads(x) for x in (root/'games.jsonl').read_text().splitlines()]
    result={'records':len(rows),'valid':sum(r['valid'] for r in rows),'errors':sum(not r['valid'] for r in rows),
            'counts':dict(Counter(f"{r['base']}_{r['variant']}" for r in rows)),
            'evaluation_methods':dict(Counter(r.get('evaluation','full_game') for r in rows)),
            'error_counters':dict(sum((Counter(r.get('errors',{})) for r in rows),Counter())),
            'results':{f'{b}_{v}':summary(rows,b,v) for b in ('m15ens','mix4') for v in ('terminal','a1','a2')}}
    (root/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({**{k:v for k,v in result.items() if k!='results'},'results':{k:{x:y for x,y in v.items() if x not in ('families','opponents','note')} for k,v in result['results'].items()}},indent=2))

if __name__=='__main__':main()
