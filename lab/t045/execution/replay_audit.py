"""Exact terminal-only counterfactual on cached real replays, never new trajectories."""
import contextlib
import copy
import gzip
import io
import json
from pathlib import Path
from types import SimpleNamespace
from build import unit_engine_source
from terminal import liquidate


def main():
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        import kaggle_environments.envs.kaggriculture.kaggriculture as K
    vendor={};exec(unit_engine_source(),vendor)
    rows=[]
    for path in Path('/workspace/shared/research/t045_replays').glob('*.gz'):
        with gzip.open(path,'rt') as f:d=json.load(f)
        before=d['steps'][-2];obs=before[0]['observation'];actions=[x['action'] for x in d['steps'][-1]]
        assert obs['step']==718
        def finish(who=None):
            o=copy.deepcopy(obs);priv=[copy.deepcopy(x['observation']['private']) for x in before]
            acts=copy.deepcopy(actions)
            if who is not None:
                own=copy.deepcopy(o);own['private']=copy.deepcopy(priv[who]);own['player']=who
                acts[who]=liquidate(own,acts[who],d['configuration'],vendor,True)
            for p in (0,1):
                ua=[acts[p].get('farmer',['PASS'])]+acts[p].get('hands',[])
                demand={}
                for a in ua:
                    if a and a[0]=='PLANT':demand[a[1]]=demand.get(a[1],0)+1
                blocked={it for it,n in demand.items() if n>priv[p]['seeds'].get(it,0)}
                for i,a in enumerate(ua):
                    if a and a[0]=='PLANT' and a[1] in blocked:a=['PASS']
                    K._apply_unit_action(o['farms'][p],priv[p],i,a,10,29,24,100)
            st=[SimpleNamespace(action=acts[p],observation=SimpleNamespace(farms=o['farms'],market=o['market'],private=priv[p])) for p in (0,1)]
            K._process_market(st,SimpleNamespace(configuration=d['configuration']))
            return [f['money'] for f in o['farms']],acts
        baseline,_=finish();assert baseline==d['rewards']
        for p in (0,1):
            new,acts=finish(p)
            rows.append(dict(episode=d['info']['EpisodeId'],team=d['info']['TeamNames'][p],seat=p,exact_baseline=True,
                             before=baseline,after=new,delta_cash=new[p]-baseline[p],
                             delta_margin=(new[p]-new[1-p])-(baseline[p]-baseline[1-p]),
                             market_before=actions[p]['market'],market_after=acts[p]['market']))
    out=Path('/workspace/shared/research/t045_terminal_v2_replay_audit.json');out.write_text(json.dumps(rows,indent=2,ensure_ascii=False))
    for r in rows:print({k:v for k,v in r.items() if not k.startswith('market')})

if __name__=='__main__':main()
