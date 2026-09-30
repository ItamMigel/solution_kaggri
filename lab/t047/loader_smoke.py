"""Official file loading versus the matching audited callable gate games."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[k]='1'
import contextlib
import io
import json
import random
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=Path('/workspace/shared/runs/t047_m26_post')


def game(job):
    variant,seat=job
    seed=93047001
    start=time.monotonic()
    log=io.StringIO()
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        import numpy as np
        from kaggle_environments import make
        random.seed(seed)
        np.random.seed(seed)
        pair=[str(HERE/'exports/m26/main.py')]*2
        pair[seat]=str(HERE/'exports'/variant/'main.py')
        env=make('kaggriculture',configuration={'seed':seed},debug=False)
        env.run(pair)
    r=dict(variant=variant,seed=seed,seat=seat,status=[s.status for s in env.state],
           rewards=[s.reward for s in env.state],seconds=time.monotonic()-start,
           remaining_overage=[s.observation.remainingOverageTime for s in env.state],log_tail=log.getvalue()[-1000:])
    rows=[json.loads(x) for x in (OUT/'games.jsonl').read_text().splitlines()]
    match=[x for x in rows if (x['variant'],x['opp'],x['seed'],x['seat'])==(variant,'m26',seed,seat)]
    assert len(match)==1 and match[0]['valid']
    r['parity']=r['status']==['DONE','DONE'] and r['rewards']==match[0]['rewards']
    return r


if __name__=='__main__':
    jobs=[(v,p) for v in ('terminal','a1','dsm75_mg25') for p in (0,1)]
    with ProcessPoolExecutor(max_workers=6) as pool:
        rows=list(pool.map(game,jobs))
    (OUT/'loader_smoke.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps(rows,indent=2))
    assert all(x['parity'] for x in rows)
