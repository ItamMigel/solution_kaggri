"""Fresh paired official full games; no replay/identity shortcuts."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
os.environ['BC3_STATS']='1'
import argparse
import contextlib
import gc
import hashlib
import importlib.util
import io
import json
import random
import signal
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = Path('/workspace/shared/candidates/t047_m26_terminal/pkg/main.py')
OPPS = {'base': BASE, **{n: HERE.parent/'t045/execution/frozen'/f'{n}.py' for n in ('tetsu','ozer44')}}

def load(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def game(job):
    variant,opp,seed,seat=job
    r=dict(variant=variant,opp=opp,seed=seed,seat=seat)
    log=io.StringIO(); latencies=[[],[]]; errors=[0,0]; start=time.monotonic()
    def alarm(*args):
        raise TimeoutError('host guard 1200s')
    signal.signal(signal.SIGALRM,alarm); signal.alarm(1200)
    try:
        with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
            from kaggle_environments import make
            random.seed(seed); np.random.seed(seed)
            mods=[None,None]
            mods[1-seat]=load(OPPS[opp],'t048_opponent')
            path=BASE if variant=='base' else HERE/'exports'/variant/'main.py'
            mods[seat]=load(path,'t048_candidate')
            agents=[]
            for i,mod in enumerate(mods):
                if hasattr(mod,'_AG'):
                    core_stats=getattr(mod._AG,'stats',{})
                    def core(*args,_core=mod._AG,_i=i,**kwargs):
                        try:
                            return _core(*args,**kwargs)
                        except Exception:
                            errors[_i]+=1
                            raise
                    core.stats=core_stats
                    mod._AG=core
                def measured(obs,config=None,_mod=mod,_i=i):
                    t=time.perf_counter()
                    try:
                        return _mod.agent(obs,config)
                    finally:
                        latencies[_i].append(time.perf_counter()-t)
                agents.append(measured)
            env=make('kaggriculture',configuration={'seed':seed},debug=False)
            env.run(agents)
            r.update(status=[s.status for s in env.state],rewards=[s.reward for s in env.state],
                     calls=list(map(len,latencies)),remaining_overage=[s.observation.remainingOverageTime for s in env.state],
                     errors=[{'bc':errors[i],'hg':getattr(m,'_HG_STATS',{}).get('errors',0),
                              **getattr(m,'_T047_ERRORS',{}),'t048':getattr(getattr(m,'_T048',None),'stats',{}).get('errors',0)}
                             for i,m in enumerate(mods)],
                     telemetry=[{'hg':getattr(m,'_HG_STATS',{}),'bc':getattr(getattr(m,'_AG',None),'stats',{}),
                                 't048':getattr(getattr(m,'_T048',None),'stats',{})} for m in mods],
                     latency=[{'max':max(x,default=0),'p50':float(np.quantile(x,.5)) if x else 0,
                               'p99':float(np.quantile(x,.99)) if x else 0,'overage':sum(max(0,t-1) for t in x)} for x in latencies])
            assert r['status']==['DONE','DONE'],r['status']
            assert r['calls']==[719,719],r['calls']
            assert not any(v for e in r['errors'] for v in e.values()),r['errors']
            assert all(x['overage']<55 for x in r['latency']),r['latency']
            r['margin']=r['rewards'][seat]-r['rewards'][1-seat]
            r['points']=float(r['margin']>0)+.5*float(r['margin']==0)
            r['valid']=True
    except BaseException:
        r.update(valid=False,exception=traceback.format_exc())
    finally:
        signal.alarm(0)
    r.update(seconds=time.monotonic()-start,log_tail=log.getvalue()[-1400:])
    gc.collect()
    return r

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--stage',choices=['screen','gate'],default='gate')
    ap.add_argument('--workers',type=int,default=6)
    a=ap.parse_args(); assert 1<=a.workers<=6
    variants=('sale_beam','late_ev')
    if a.stage=='screen':
        jobs=[(v,o,s,p) for s in (93048203,93048204) for o in OPPS for v in variants for p in (0,1)]
    else:
        jobs=[(v,'base',s,p) for s in range(93048501,93048517) for v in variants for p in (0,1)]
        jobs += [(v,o,s,p) for s in range(93048601,93048609) for o in ('tetsu','ozer44')
                 for v in (*variants,'base') for p in (0,1)]
    build=json.loads((HERE/'manifest.json').read_text())
    for rec in [build['base'],*build['exports'].values()]:
        assert hashlib.sha256(Path(rec['path']).read_bytes()).hexdigest()==rec['sha256']
    manifest=dict(build=build,jobs=jobs,stage=a.stage,workers=a.workers,
                  opponents={k:{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for k,p in OPPS.items()},
                  rule='Each: 16 NEW worlds both seats h2h points>=.65 AND two-sided95 whole-world-bootstrap margin lower>0; '
                       '8 different worlds both seats each tetsu/ozer44 with paired unchanged-base control, no points regression '
                       'and mean margin no worse on either sanity opponent; all errors/timeouts0. '
                       'No variant tuning after gate starts. Bootstrap100000,RNG48020260930. '
                       'The sanity rule is a finite-panel screen, not a proof of non-inferiority.')
    a.out.mkdir(parents=True,exist_ok=True); mf=a.out/'manifest.json'
    if mf.exists():
        assert json.loads(mf.read_text())==json.loads(json.dumps(manifest))
    else:
        mf.write_text(json.dumps(manifest,indent=2))
    results=a.out/'games.jsonl'; done=set()
    if results.exists():
        for line in results.read_text().splitlines():
            r=json.loads(line); assert r['valid'],'Investigate invalid record before resuming'
            done.add((r['variant'],r['opp'],r['seed'],r['seat']))
    todo=[j for j in jobs if j not in done]
    with results.open('a') as f, ProcessPoolExecutor(max_workers=a.workers) as pool:
        fs=[pool.submit(game,j) for j in todo]
        for i,fut in enumerate(as_completed(fs),1):
            r=fut.result();f.write(json.dumps(r)+'\n');f.flush()
            print(i+len(done),'/',len(jobs),r['variant'],r['opp'],r['seed'],r['seat'],r.get('margin'),r['valid'],round(r['seconds'],1),flush=True)

if __name__=='__main__':
    main()
