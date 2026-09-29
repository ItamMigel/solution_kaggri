"""Official file-loader smoke, including source load against the overage budget."""
import os
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
import contextlib, io, json, random, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
HERE=Path(__file__).resolve().parent


def game(job):
    base,variant,seat=job
    import numpy as np
    random.seed(929451010);np.random.seed(929451010)
    log=io.StringIO();start=time.monotonic()
    with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
        from kaggle_environments import make
        env=make('kaggriculture',configuration={'seed':929451010},debug=False)
        pair=[str(HERE/'frozen/tetsu.py')]*2;pair[seat]=str(HERE/'exports'/f'{base}_{variant}.py')
        env.run(pair)
    rec=dict(base=base,variant=variant,seat=seat,status=[s.status for s in env.state],rewards=[s.reward for s in env.state],
             seconds=time.monotonic()-start,remaining_overage=[s.observation.remainingOverageTime for s in env.state],output_tail=log.getvalue()[-1000:])
    assert rec['status']==['DONE','DONE'],rec
    return rec

if __name__=='__main__':
    jobs=[(b,v,p) for b in ('m15ens','mix4') for v in ('off','terminal','a1','a2') for p in (0,1)]
    with ProcessPoolExecutor(max_workers=8) as pool:
        rows=list(pool.map(game,jobs))
    Path('/workspace/shared/runs/t045_execution_loader_smoke.json').write_text(json.dumps(rows,indent=2))
    for r in rows:print(json.dumps(r))
