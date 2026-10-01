"""Small T046 team-label development screen. Never touches T045 outputs or processes."""
import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import sys
sys.dont_write_bytecode = True
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import random
import time
import traceback
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import numpy as np

PAVEL = Path('/workspace/shared/pavel_lab/lab/pavel')
BASE = PAVEL / 'candidates/bc_hg_m15ens_d13/main.py'
OPPS = {
    'tetsu': str(PAVEL / 'candidates/tetsu1009_public/main.py'),
    'yaxon5': '/workspace/shared/opponents/pool/yaxon_reactive_v5/main.py',
    'parthenos': '/workspace/shared/opponents/pool/parthenos_robust/main.py',
}
VARIANTS = ('baseline', 'mg2', 'mg75_mg2', 'mg75_decem')


def load(path):
    spec = importlib.util.spec_from_file_location('t046_frozen', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def configure(mod, variant, counts):
    members = mod._AG.model.m
    if variant == 'baseline':
        return
    label = 'decem_cn' if variant == 'mg75_decem' else 'mgoose2_cn'
    assert all(label in x.cfg['teams'] for x in members)
    if variant == 'mg2':
        mod._AG.team_vec[:] = 0
        mod._AG.team_vec[members[0].cfg['teams'].index(label)] = 1
        return

    # This frozen m15 export predates current export3.py: Agent appends the label,
    # while _NpOne consumes the already augmented G. Rewrite G at each member
    # boundary; assigning a .tv attribute would be silently ineffective here.
    class Style:
        def __init__(self, member):
            self.member = member
            self.cfg = member.cfg
            self.n = len(self.cfg['teams'])
            self.i = self.cfg['teams'].index(label)
        def __getattr__(self, name):
            return getattr(self.member,name)
        def glob(self,G):
            g=G.copy(); g[:,-self.n:]=0; g[:,-self.n+self.i]=1
            return g
        def encode(self,B,G):
            return self.member.encode(B,self.glob(G))
        def units(self,h,G,ux,uy,uv):
            return self.member.units(h,self.glob(G),ux,uy,uv)
        def m_start(self,h,G,MS):
            return self.member.m_start(h,self.glob(G),MS)
    extra = [Style(x) for x in members]

    class Weighted(mod._Ens):
        def __init__(self):
            super().__init__(members + extra)
            self.w = np.array([.375, .375, .125, .125], dtype=np.float32)

        def mix(self, xs):
            return np.einsum('m,m...->...', self.w, np.stack(xs))

        def disagree(self, xs, key):
            left = np.mean(xs[:2], 0).argmax(-1)
            right = np.mean(xs[2:], 0).argmax(-1)
            counts[key + '_disagree'] += int(np.count_nonzero(left != right))
            counts[key + '_n'] += int(np.size(left))

        def units(self, hs, G, ux, uy, uv):
            outs = [x.units(h, G, ux, uy, uv) for x, h in zip(self.m, hs)]
            self.disagree([o[0] for o in outs], 'op')
            self.disagree([o[1] for o in outs], 'target')
            return self.mix([o[0] for o in outs]), self.mix([o[1] for o in outs]), [o[2] for o in outs]

        def qty(self, zs, i, cls):
            return self.mix([x.qty(z, i, cls) for x, z in zip(self.m, zs)])

        def m_step(self, sts, prev_t, prev_q, sl):
            outs = [x.m_step(st, prev_t, prev_q, sl) for x, st in zip(self.m, sts)]
            self.disagree([o[1] for o in outs], 'market')
            return [o[0] for o in outs], self.mix([o[1] for o in outs])

        def m_qty(self, sts, tok):
            return self.mix([x.m_qty(st, tok) for x, st in zip(self.m, sts)])

    mod._AG.model = Weighted()


def game(spec):
    variant, opp, seed, seat = spec
    t0 = time.perf_counter()
    counts = Counter()
    times = []
    log = io.StringIO()
    rec = dict(variant=variant, opp=opp, seed=seed, seat=seat)
    try:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            random.seed(seed)
            np.random.seed(seed)
            from kaggle_environments import make
            mod = load(BASE)
            configure(mod, variant, counts)
            def wrapped(obs, config=None):
                now = time.perf_counter()
                try:
                    a = mod._AG(obs, config)
                    a = mod._hg_apply(obs, a)
                except Exception:
                    counts['exceptions'] += 1
                    raise
                counts['calls'] += 1
                times.append(time.perf_counter() - now)
                return a
            env = make('kaggriculture', configuration={'seed': seed}, debug=False)
            pair = [None, None]
            pair[seat] = wrapped
            pair[1-seat] = OPPS[opp]
            env.run(pair)
            rewards = [s.reward for s in env.state]
            rec.update(status=[s.status for s in env.state], rewards=rewards,
                       margin=rewards[seat]-rewards[1-seat],
                       score=float(rewards[seat]>rewards[1-seat])+.5*float(rewards[seat]==rewards[1-seat]),
                       hg_stats=mod._HG_STATS)
    except Exception:
        rec['error'] = traceback.format_exc()
    rec.update(seconds=time.perf_counter()-t0, counts=dict(counts),
               latency={k: float(v) for k,v in zip(('p50','p99','max'),
                         (np.median(times), np.quantile(times,.99), max(times)))} if times else {},
               overage=sum(max(0,t-1) for t in times), log_tail=log.getvalue()[-1200:])
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--worlds', type=int, default=8)
    ap.add_argument('--variants', default=','.join(VARIANTS))
    ap.add_argument('--opponents', default=','.join(OPPS))
    ap.add_argument('--resume', action='store_true')
    a = ap.parse_args()
    assert 1 <= a.workers <= 12
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=a.resume)
    seeds = list(range(92946001, 92946001+a.worlds))
    variants = a.variants.split(',')
    opponents = {o:OPPS[o] for o in a.opponents.split(',')}
    assert all(v in VARIANTS for v in variants)
    manifest = dict(seeds=seeds, variants=variants, opponents=opponents, workers=a.workers,
                    base=str(BASE), sha256={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest()
                    for p in [BASE, *OPPS.values()]},
                    rule='Development only: paired whole-world score CI, no promotion from this screen; no retuning weights.')
    if a.resume:
        old_manifest = json.loads((out/'manifest.json').read_text())
        assert old_manifest['sha256'] == manifest['sha256']
        assert old_manifest['variants'] == manifest['variants']
        assert old_manifest['opponents'] == manifest['opponents']
        (out/'resume_manifest.json').write_text(json.dumps(manifest,indent=2))
    else:
        (out/'manifest.json').write_text(json.dumps(manifest, indent=2))
    specs = [(v,o,s,p) for s in seeds for o in opponents for p in (0,1) for v in variants]
    if a.resume:
        done = [json.loads(x) for x in (out/'games.jsonl').read_text().splitlines() if x.strip()]
        assert all('error' not in x and x['status']==['DONE','DONE'] for x in done)
        keys = {(x['variant'],x['opp'],x['seed'],x['seat']) for x in done}
        specs = [s for s in specs if s not in keys]
    with (out/'games.jsonl').open('a' if a.resume else 'w') as f, ProcessPoolExecutor(a.workers) as ex:
        futures = [ex.submit(game, spec) for spec in specs]
        for i, fut in enumerate(as_completed(futures),1):
            rec = fut.result()
            f.write(json.dumps(rec)+'\n'); f.flush()
            if i%12 == 0 or 'error' in rec:
                print(f'{i}/{len(specs)} {rec["variant"]} {rec.get("status",rec.get("error"))}', flush=True)


if __name__ == '__main__':
    main()
