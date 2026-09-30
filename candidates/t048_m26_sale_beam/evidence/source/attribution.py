"""Post-gate diagnostic: factual-state, one-step exact market counterfactuals.

These local deltas are not a decomposition of an alternative full trajectory.
No policy parameters are selected using these diagnostics.
"""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import contextlib
import copy
import io
import json
import random
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from gate import load,HERE,BASE
OUT=Path('/workspace/shared/runs/t048_ev_gate')

def game(seed):
    log=io.StringIO();events=[];last={}
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        from kaggle_environments import make
        random.seed(seed);np.random.seed(seed)
        mod=load(HERE/'exports/sale_beam/main.py','attribution_beam')
        opp=load(BASE,'attribution_base')
        apply=mod._T048.apply
        def capture(obs,action,config=None):
            before=mod._T048.stats['expected_gain']
            result=apply(obs,action,config)
            last.update(step=int(obs['step']),native=copy.deepcopy(action),changed=result!=action,
                        predicted=mod._T048.stats['expected_gain']-before)
            return result
        mod._T048.apply=capture
        env=make('kaggriculture',configuration={'seed':seed},debug=False)
        engine=env.interpreter.__globals__;market=engine['_process_market']
        def hook(state,env):
            alternate=None
            if last['changed']:
                assert last['step']==int(state[0].observation.step)
                assert state[0].action['farmer']==last['native']['farmer']
                assert state[0].action['hands']==last['native']['hands']
                alternate=copy.deepcopy(state)
                alternate[0].action=last['native']
                market(alternate,env)
            market(state,env)
            if alternate is not None:
                ours=state[0].observation.farms[0]['money']-alternate[0].observation.farms[0]['money']
                theirs=state[0].observation.farms[1]['money']-alternate[0].observation.farms[1]['money']
                assert state[0].observation.private['shed']==alternate[0].observation.private['shed']
                events.append(dict(step=last['step'],predicted=last['predicted'],local_own_delta=ours,
                                   local_rival_delta=theirs,local_margin_delta=ours-theirs,
                                   native=last['native']['market'],selected=copy.deepcopy(state[0].action['market'])))
        engine['_process_market']=hook
        try:env.run([mod.agent,opp.agent])
        finally:engine['_process_market']=market
    rows=[json.loads(x) for x in (OUT/'games.jsonl').read_text().splitlines()]
    ref=next(r for r in rows if (r['variant'],r['opp'],r['seed'],r['seat'])==('sale_beam','base',seed,0))
    result=dict(seed=seed,status=[s.status for s in env.state],rewards=[s.reward for s in env.state],events=events,
                sum_predicted=sum(r['predicted'] for r in events),
                sum_local_margin_delta=sum(r['local_margin_delta'] for r in events),
                negative_local_decisions=sum(r['local_margin_delta']<0 for r in events))
    assert result['status']==['DONE','DONE'] and result['rewards']==ref['rewards']
    return result

if __name__=='__main__':
    with ProcessPoolExecutor(max_workers=2) as pool:
        rows=list(pool.map(game,[93048501,93048513]))
    (OUT/'attribution.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
