"""Full official games, unchanged frozen exports, audited fallback and timing."""
import os
for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[k] = '1'
import argparse
import contextlib
import gc
import hashlib
import importlib.util
import io
import json
import random
import signal
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = Path('/workspace/shared/runs/t047_m26_post')
OPPS = {'m26': HERE/'exports/m26/main.py', **{n: HERE.parent/'t045/execution/frozen'/f'{n}.py' for n in ('tetsu', 'ozer44')}}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def game(job):
    variant, opp, seed, seat = job
    r = dict(variant=variant, opp=opp, seed=seed, seat=seat)
    start = time.monotonic()
    log = io.StringIO()
    latencies = [[], []]
    errors = [0, 0]
    def alarm(*args):
        raise TimeoutError('host guard 1500s')
    signal.signal(signal.SIGALRM, alarm)
    signal.alarm(1500)
    try:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            from kaggle_environments import make
            random.seed(seed)
            np.random.seed(seed)
            mods = [load(OPPS[opp], 't047_opp'), None]
            mods[1] = mods[0]
            mods[seat] = load(HERE/'exports'/variant/'main.py', 't047_candidate')
            agents = []
            for i, mod in enumerate(mods):
                if hasattr(mod, '_AG'):
                    def core(*args, _core=mod._AG, _i=i, **kwargs):
                        try:
                            return _core(*args, **kwargs)
                        except Exception:
                            errors[_i] += 1
                            raise
                    mod._AG = core
                def measured(obs, config=None, _mod=mod, _i=i):
                    t0 = time.perf_counter()
                    try:
                        return _mod.agent(obs, config)
                    finally:
                        latencies[_i].append(time.perf_counter()-t0)
                agents.append(measured)
            env = make('kaggriculture', configuration={'seed': seed}, debug=False)
            env.run(agents)
            r.update(status=[s.status for s in env.state], rewards=[s.reward for s in env.state],
                     errors=[{'bc': errors[i], 'hg': getattr(m, '_HG_STATS', {}).get('errors', 0),
                              **getattr(m, '_T047_ERRORS', {})} for i, m in enumerate(mods)],
                     calls=list(map(len, latencies)),
                     latency=[{'max': max(x, default=0), 'p99': float(np.quantile(x, .99)) if x else 0,
                               'overage': sum(max(0, t-1) for t in x)} for x in latencies],
                     remaining_overage=[s.observation.remainingOverageTime for s in env.state])
            assert r['status'] == ['DONE', 'DONE'], r['status']
            assert r['calls'] == [719, 719], r['calls']
            assert not any(v for e in r['errors'] for v in e.values()), r['errors']
            assert all(x['overage'] < 55 for x in r['latency']), r['latency']
            r.update(margin=r['rewards'][seat]-r['rewards'][1-seat])
            r['points'] = float(r['margin'] > 0) + .5*float(r['margin'] == 0)
            r['valid'] = True
    except BaseException:
        r.update(valid=False, exception=traceback.format_exc())
    finally:
        signal.alarm(0)
    r.update(seconds=time.monotonic()-start, log_tail=log.getvalue()[-1200:])
    gc.collect()
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=11)
    a = ap.parse_args()
    assert 1 <= a.workers <= 11
    OUT.mkdir(parents=True, exist_ok=True)
    variants = ('terminal', 'a1', 'dsm75_mg25')
    jobs = [(v, 'm26', s, p) for s in range(93047001,93047017) for v in variants for p in (0,1)]
    jobs += [(v, o, s, p) for s in range(93047101,93047109) for o in ('tetsu','ozer44') for v in variants for p in (0,1)]
    manifest = dict(build=json.loads((HERE/'manifest.json').read_text()), jobs=jobs, workers=a.workers,
                    opponents={k:{'path':str(p), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for k,p in OPPS.items()},
                    rule='32 full h2h games each: points >= .65, mean margin > 0, two-sided 95% whole-world bootstrap lower > 0; zero errors/timeouts in all games; no adaptive tuning')
    mf = OUT/'manifest.json'
    if mf.exists():
        assert json.loads(mf.read_text()) == json.loads(json.dumps(manifest))
    else:
        mf.write_text(json.dumps(manifest, indent=2))
    results = OUT/'games.jsonl'
    done = set()
    if results.exists():
        for line in results.read_text().splitlines():
            r = json.loads(line)
            assert r['valid'], 'Invalid result retained; investigate before restarting'
            done.add((r['variant'],r['opp'],r['seed'],r['seat']))
    jobs = [j for j in jobs if j not in done]
    with results.open('a') as f, ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(game, j) for j in jobs]
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            f.write(json.dumps(r)+'\n')
            f.flush()
            print(i+len(done), '/192', r['variant'], r['opp'], r['seed'], r['seat'], r.get('margin'), r['valid'], round(r['seconds'],1), flush=True)


if __name__ == '__main__':
    main()
