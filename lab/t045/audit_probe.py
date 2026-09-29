"""Bounded, read-only audit of Pavel's frozen BC+HG export; no training."""
import os
for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "1"
os.environ["BC3_STATS"] = "1"
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

PAVEL = Path('/workspace/shared/pavel_lab/lab/pavel')
BASE = PAVEL / 'candidates/bc_hg_m15ens_d13/main.py'
OPPS = {
    'tetsu': str(PAVEL / 'candidates/tetsu1009_public/main.py'),
    'yaxon5': '/workspace/shared/opponents/pool/yaxon_reactive_v5/main.py',
}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def synthetic():
    ns = {'agent': lambda obs, config=None: {}}
    exec((PAVEL / 'hg/hg_layer_v2.py').read_text(), ns)
    tiles = [[None for _ in range(10)] for _ in range(10)]
    for x in (4, 5):
        tiles[4][x] = dict(kind='PASTURE', animal='COW', consecutive_unfed=1, fed_today=False)
    obs = {'player': 0, 'step': 23, 'farms': [dict(tiles=tiles, farmer=[4, 4], hands=[], money=0)],
           'private': {'shed': {}, 'inventories': [{'WHEAT': 2}]}, 'market': {'prices': {'WHEAT': 30}}}
    old = {'farmer': ['FEED'], 'hands': [], 'market': []}
    new = ns['_hg_apply'](copy.deepcopy(obs), copy.deepcopy(old))
    result = {'native_feed_overwrite': {'before': old, 'after': new, 'hour': 23}}
    assert new['farmer'] == ['EAST']
    obs['farms'][0]['farmer'] = [0, 0]
    obs['private']['inventories'] = [{'WHEAT': 1}]
    old = {'farmer': ['HARVEST'], 'hands': [], 'market': []}
    result['unreachable_override'] = {'before': old, 'after': ns['_hg_apply'](obs, copy.deepcopy(old))}
    obs['step'] = 24
    obs['farms'][0]['farmer'] = [4, 4]
    obs['farms'][0]['money'] = 0
    obs['private'] = {'shed': {'MILK': 10}, 'inventories': [{}]}
    old = {'farmer': ['PASS'], 'hands': [], 'market': [['SELL', 'MILK', 10]]}
    result['sale_funded_wheat_missing'] = {'before': old, 'after': ns['_hg_apply'](obs, copy.deepcopy(old))}
    obs['private'] = {'shed': {'WHEAT': 2}, 'inventories': [{}]}
    old = {'farmer': ['PASS'], 'hands': [], 'market': [['SELL', 'WHEAT', 2]]}
    result['reserve_sold_away'] = {'before': old, 'after': ns['_hg_apply'](obs, copy.deepcopy(old))}
    return result


def game(spec):
    opp, seed, seat, out, variant = spec
    import numpy as np
    import random
    random.seed(seed)
    np.random.seed(seed)
    log = io.StringIO()
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        from kaggle_environments import make
        mod = load_module(BASE, 't045_frozen')
        if variant in ('target_prob', 'all_prob'):
            def mix(v):
                return np.logaddexp.reduce(np.stack(v), axis=0) - np.log(len(v))
            def units(self, hs, G, ux, uy, uv):
                outputs = [x.units(h, G, ux, uy, uv) for x, h in zip(self.m, hs)]
                op = mix([v[0] for v in outputs]) if variant == 'all_prob' else np.mean([v[0] for v in outputs], 0)
                return op, mix([v[1] for v in outputs]), [v[2] for v in outputs]
            mod._Ens.units = units
            if variant == 'all_prob':
                mod._Ens.qty = lambda self, zs, i, cls: mix([x.qty(z, i, cls) for x, z in zip(self.m, zs)])
                def m_step(self, sts, prev_t, prev_q, sl):
                    outputs = [x.m_step(st, prev_t, prev_q, sl) for x, st in zip(self.m, sts)]
                    return [v[0] for v in outputs], mix([v[1] for v in outputs])
                mod._Ens.m_step = m_step
                mod._Ens.m_qty = lambda self, sts, tok: mix([x.m_qty(st, tok) for x, st in zip(self.m, sts)])
        elif variant == 'trustop':
            mod._AG.trustop = True
        elif variant not in ('baseline', 'terminal_sell'):
            raise ValueError(variant)
        load_seconds = time.perf_counter() - t0
        counts = Counter()
        examples = []
        times = []

        def wrapped(obs, config=None):
            start = time.perf_counter()
            try:
                action = mod._AG(obs, config)
            except Exception as exc:
                counts['bc_exceptions'] += 1
                raise exc
            before = copy.deepcopy(action)
            after = mod._hg_apply(obs, action)
            if variant == 'terminal_sell' and obs['step'] == 718:
                from terminal_sell import top_up
                ua = [after.get('farmer')] + after.get('hands', [])
                post = mod.F.shed_after_units(obs, obs['player'], ua)
                shed = {it: int(round(v * 50)) for it, v in zip(mod.F.ITEMS, post)}
                after = top_up(after, shed, obs['market']['prices'])
            ba = [before.get('farmer')] + before.get('hands', [])
            aa = [after.get('farmer')] + after.get('hands', [])
            invs = obs['private']['inventories']
            farm = obs['farms'][obs['player']]
            pos = [farm['farmer']] + farm['hands']
            for i, (b, a) in enumerate(zip(ba, aa)):
                if b != a:
                    counts['unit_changes'] += 1
                    if b and b[0] == 'FEED' and invs[i].get('WHEAT', 0):
                        x, y = pos[i]
                        tile = farm['tiles'][y][x]
                        if isinstance(tile, dict) and tile.get('animal') and not tile.get('fed_today'):
                            counts['valid_native_feed_overwritten'] += 1
                            if len(examples) < 8:
                                examples.append(dict(step=obs['step'], unit=i, before=b, after=a,
                                                     pos=pos[i], wheat=invs[i].get('WHEAT', 0), tile=dict(tile)))
            counts['calls'] += 1
            counts['market_changes'] += before['market'] != after['market']
            counts['max_hands'] = max(counts['max_hands'], len(farm['hands']))
            counts['full_market'] += len(after['market']) == 10
            times.append(time.perf_counter() - start)
            return after

        env = make('kaggriculture', configuration={'seed': seed}, debug=False)
        pair = [None, None]
        pair[seat] = wrapped
        pair[1 - seat] = OPPS[opp]
        env.run(pair)
    rec = dict(variant=variant, opp=opp, seed=seed, seat=seat, rewards=[s.reward for s in env.state],
               status=[s.status for s in env.state], seconds=time.perf_counter() - t0,
               import_and_load_seconds=load_seconds, counts=dict(counts), examples=examples,
               hg_stats=mod._HG_STATS, bc_stats=mod._AG.stats,
               latency=dict(p50=float(np.median(times)), p95=float(np.quantile(times, .95)),
                            p99=float(np.quantile(times, .99)), max=max(times),
                            over_one_second_total=sum(max(0, t-1) for t in times)),
               swallowed_output_tail=log.getvalue()[-1000:])
    Path(out, f'{variant}_{opp}_{seed}_{seat}.json').write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return {k: rec[k] for k in ('variant', 'opp', 'seed', 'seat', 'rewards', 'status', 'seconds', 'counts', 'latency')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--games', action='store_true')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--variants', default='baseline')
    ap.add_argument('--seeds', default='92645001,92645002')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    result = synthetic()
    (out / 'synthetic.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (out / 'manifest.json').write_text(json.dumps({'base': str(BASE), 'sha256': hashlib.sha256(BASE.read_bytes()).hexdigest(),
                                                  'opponents': OPPS, 'threads_per_worker': 1}, indent=2))
    print(json.dumps(result), flush=True)
    if a.games:
        jobs = [(opp, int(seed), seat, str(out), variant) for variant in a.variants.split(',')
                for opp in OPPS for seed in a.seeds.split(',') for seat in (0, 1)]
        with ProcessPoolExecutor(max_workers=min(16, a.workers)) as pool:
            for rec in pool.map(game, jobs):
                print(json.dumps(rec), flush=True)


if __name__ == '__main__':
    main()
