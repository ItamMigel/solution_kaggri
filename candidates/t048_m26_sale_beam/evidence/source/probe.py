"""Development diagnostics only; private opponent data never used by a policy."""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import contextlib
import copy
import gzip
import importlib.util
import io
import json
import random
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = Path('/workspace/shared/runs/t048_dev_probe')
BASE = Path('/workspace/shared/candidates/t047_m26_terminal/pkg/main.py')
OPPS = {'base': BASE, **{x: HERE.parent/'t045/execution/frozen'/f'{x}.py' for x in ('tetsu','ozer44')}}

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def game(job):
    opp, seed, seat = job
    start = time.monotonic()
    records = []
    timings = []
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        from kaggle_environments import make
        random.seed(seed); np.random.seed(seed)
        pair = [load(OPPS[opp], 'probe_opp').agent, None]
        pair[1] = pair[0]
        mod = load(BASE, 'probe_base')
        def act(obs, config=None):
            t0 = time.perf_counter()
            a = mod.agent(obs, config)
            timings.append(time.perf_counter()-t0)
            return a
        pair[seat] = act
        env = make('kaggriculture', configuration={'seed': seed}, debug=False)
        engine = env.interpreter.__globals__
        old = engine['_process_market']
        def hook(state, env):
            obs = state[0].observation
            rec = {'step': obs.step, 'market': copy.deepcopy(obs.market), 'town': copy.deepcopy(obs.town),
                   'orders': [copy.deepcopy(s.action.get('market', [])) for s in state],
                   'shed': [copy.deepcopy(s.observation.private.shed) for s in state],
                   'cargo': [copy.deepcopy(s.observation.private.inventories) for s in state],
                   'money_before': [f['money'] for f in obs.farms],
                   'ripe': [{it: sum(int(t.get('yield_units',0)) for row in f['tiles'] for t in row
                                         if isinstance(t,dict) and (t.get('crop')==it or
                                             {'COW':'MILK','SHEEP':'WOOL','GOOSE':'EGG'}.get(t.get('animal'))==it))
                             for it in engine['PRODUCTS']} for f in obs.farms]}
            old(state, env)
            rec.update(money_after=[f['money'] for f in obs.farms],
                       market_after=copy.deepcopy(obs.market),
                       shed_after=[copy.deepcopy(s.observation.private.shed) for s in state])
            records.append(rec)
        engine['_process_market'] = hook
        try:
            env.run(pair)
        finally:
            engine['_process_market'] = old
    r = dict(opp=opp, seed=seed, seat=seat, status=[s.status for s in env.state],
             rewards=[s.reward for s in env.state], max_call=max(timings),
             seconds=time.monotonic()-start, records=records)
    with gzip.open(OUT/f'{opp}_{seed}_{seat}.json.gz','wt') as f:
        json.dump(r, f)
    return {k:v for k,v in r.items() if k!='records'}

if __name__ == '__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    jobs=[(o,s,p) for s in (93048201,93048202) for o in OPPS for p in (0,1)]
    with ProcessPoolExecutor(max_workers=6) as pool:
        futs=[pool.submit(game,j) for j in jobs]
        rows=[]
        for f in as_completed(futs):
            rows.append(f.result()); print(json.dumps(rows[-1]),flush=True)
    (OUT/'summary.json').write_text(json.dumps(rows,indent=2))
