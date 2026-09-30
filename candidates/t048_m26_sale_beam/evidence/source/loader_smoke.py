"""Official file-loader parity and full-episode off identity. <=6 workers."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[k]='1'
import contextlib
import argparse
import copy
import hashlib
import io
import json
import random
import signal
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from gate import load, HERE, BASE
OUT=Path('/workspace/shared/runs/t048_ev_gate')

def game(job):
    variant,seat=job;seed=93048501;log=io.StringIO();t0=time.monotonic()
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        from kaggle_environments import make
        random.seed(seed);np.random.seed(seed)
        path=HERE/'exports'/variant/'main.py'
        pair=[str(BASE),str(BASE)];pair[seat]=str(path)
        env=make('kaggriculture',configuration={'seed':seed},debug=False);env.run(pair)
        r=dict(variant=variant,seat=seat,seed=seed,status=[s.status for s in env.state],
               rewards=[s.reward for s in env.state],remaining_overage=[s.observation.remainingOverageTime for s in env.state])
        if variant=='off':
            random.seed(seed);np.random.seed(seed)
            wrapper=load(path,'off_shadow');base=load(BASE,'off_parent');opp=load(BASE,'off_opp')
            diffs=[];calls=0
            def measured(obs,config=None):
                nonlocal calls
                before=copy.deepcopy(obs)
                a=base.agent(obs,config);b=wrapper.agent(obs,config)
                assert obs==before,'Observation mutated'
                if a!=b:diffs.append(int(obs['step']))
                calls+=1
                return b
            agents=[opp.agent,opp.agent];agents[seat]=measured
            ref=make('kaggriculture',configuration={'seed':seed},debug=False);ref.run(agents)
            expected=[s.reward for s in ref.state]
            r.update(identity_calls=calls,identity_diffs=diffs,reference_status=[s.status for s in ref.state])
            assert calls==719 and not diffs and r['reference_status']==['DONE','DONE']
        else:
            rows=[json.loads(x) for x in (OUT/'games.jsonl').read_text().splitlines()]
            match=[x for x in rows if (x['variant'],x['opp'],x['seed'],x['seat'])==(variant,'base',seed,seat)]
            assert len(match)==1 and match[0]['valid']
            expected=match[0]['rewards']
        r.update(parity=r['status']==['DONE','DONE'] and r['rewards']==expected,
                 seconds=time.monotonic()-t0,log_tail=log.getvalue()[-1200:])
    return r

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=4)
    args=ap.parse_args();assert 1<=args.workers<=6
    manifest=json.loads((OUT/'manifest.json').read_text())['build']
    for rec in [manifest['base'],*manifest['exports'].values()]:
        assert hashlib.sha256(Path(rec['path']).read_bytes()).hexdigest()==rec['sha256']
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows=list(pool.map(game,[(v,p) for v in ('off','sale_beam','late_ev') for p in (0,1)]))
    (OUT/'loader_smoke.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
    assert all(r['parity'] for r in rows)
