"""Small, reproducible Monte-Carlo PPO loop for the daily Horizon knob policy.

Each rollout uses the official kaggle-environments engine in an isolated
process.  A noisy daily policy and its deterministic static anchor play the
same seed, seat and reactive opponent.  The paired terminal score/margin is
therefore the reward.  This is intentionally a modest real-engine loop, not a
claim that raw action RL is cheap enough for the remaining competition time.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from knobs import base_params
from ppo_horizon import FEATURES, NAMES, make_daily_agent_file, zero_weights

PANEL = {
    'v5_market': '/workspace/wt/codex/agents/horizon_v5_market.py',
    'yhay0913': '/workspace/shared/opponents/pool/yhay_router0913/main.py',
    'yhay0909': '/workspace/shared/opponents/pool/yhay_router0909/main.py',
    'parthenos': '/workspace/shared/opponents/pool/parthenos_robust/main.py',
    'metav4': '/workspace/shared/opponents/pool/tschinkel_metav4_v13/main.py',
    't2945': '/workspace/shared/opponents/pool/tschinkel2945/main.py',
}


def load_json(path):
    obj = json.loads(Path(path).read_text())
    return obj.get('params', obj)


def stable_seed(*parts):
    raw = '|'.join(map(str, parts)).encode()
    return int.from_bytes(hashlib.blake2s(raw, digest_size=4).digest(), 'little')


def call_worker(job, timeout):
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, str(HERE/'ppo_game_worker.py')], input=json.dumps(job),
            text=True, capture_output=True, timeout=timeout, cwd=str(HERE))
        if proc.returncode:
            return {**{k: job[k] for k in ('kind', 'seed', 'seat', 'opponent')},
                    'error': 'worker process failed', 'detail': (proc.stderr or proc.stdout)[-2000:]}
        row = json.loads(proc.stdout)
        row['seconds'] = time.perf_counter() - started
        return row
    except subprocess.TimeoutExpired:
        return {**{k: job[k] for k in ('kind', 'seed', 'seat', 'opponent')},
                'error': 'wall timeout'}
    except Exception as exc:
        return {**{k: job[k] for k in ('kind', 'seed', 'seat', 'opponent')},
                'error': repr(exc)}


def rollout(out, weights, anchor, seeds, opponents, noise_std, workers, timeout, iteration):
    rollout_dir = out / f'iter_{iteration:03d}'
    rollout_dir.mkdir(parents=True, exist_ok=False)
    policy_path = rollout_dir/'policy.py'
    anchor_path = rollout_dir/'anchor.py'
    make_daily_agent_file(weights, policy_path, anchor=anchor, noise_std=noise_std, trace=True)
    make_daily_agent_file(zero_weights(), anchor_path, anchor=anchor)
    jobs = []
    for seed in seeds:
        for name, opponent in opponents.items():
            for seat in (0, 1):
                common = dict(seed=seed, seat=seat, opponent=name, opponent_path=opponent)
                jobs.append(dict(**common, kind='policy', candidate_path=str(policy_path),
                                 policy_seed=stable_seed(iteration, seed, name, seat)))
                jobs.append(dict(**common, kind='anchor', candidate_path=str(anchor_path)))
    manifest = dict(iteration=iteration, seeds=seeds, opponents=opponents, workers=workers,
                    noise_std=noise_std, expected_games=len(jobs), reward='paired points + paired margin/40000')
    (rollout_dir/'manifest.json').write_text(json.dumps(manifest, indent=2))
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(call_worker, job, timeout) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda r: (r['seed'], r['opponent'], r['seat'], r['kind']))
    (rollout_dir/'games.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
    if any('error' in row for row in rows):
        return rollout_dir, rows, [], {'error': 'rollout contains failed games'}
    paired = {}
    for row in rows:
        key = row['seed'], row['opponent'], row['seat']
        paired.setdefault(key, {})[row['kind']] = row
    samples = []
    rewards = []
    for key, pair in paired.items():
        policy, static = pair['policy'], pair['anchor']
        reward = ((policy['points'] - static['points']) +
                  (policy['margin'] - static['margin']) / 40000.0)
        rewards.append(reward)
        for trace in policy['trace']:
            samples.append(dict(features=trace['features'] + [1.0], raw=trace['raw'],
                                mean=trace['mean'], reward=reward))
    info = dict(games=len(rows), paired_games=len(paired), decisions=len(samples),
                reward_mean=float(np.mean(rewards)), reward_std=float(np.std(rewards)),
                policy_points=float(np.mean([x['points'] for x in rows if x['kind'] == 'policy'])),
                anchor_points=float(np.mean([x['points'] for x in rows if x['kind'] == 'anchor'])),
                policy_margin=float(np.mean([x['margin'] for x in rows if x['kind'] == 'policy'])),
                anchor_margin=float(np.mean([x['margin'] for x in rows if x['kind'] == 'anchor'])))
    (rollout_dir/'summary.json').write_text(json.dumps(info, indent=2))
    return rollout_dir, rows, samples, info


def ppo_update(weights, samples, noise_std, learning_rate, clip_ratio, epochs, seed):
    """One clipped-Gaussian PPO update using Monte-Carlo terminal advantages."""
    w = np.asarray(weights, dtype=np.float64)
    x = np.asarray([s['features'] for s in samples], dtype=np.float64)
    z = np.asarray([s['raw'] for s in samples], dtype=np.float64)
    old_mean = np.asarray([s['mean'] for s in samples], dtype=np.float64)
    advantage = np.asarray([s['reward'] for s in samples], dtype=np.float64)
    advantage = (advantage - advantage.mean()) / max(1e-8, advantage.std())
    sigma2 = noise_std ** 2
    rng = np.random.default_rng(seed)
    for _ in range(epochs):
        for index in np.array_split(rng.permutation(len(samples)), max(1, len(samples)//256)):
            xb, zb, oldb, advb = x[index], z[index], old_mean[index], advantage[index]
            mean = xb @ w.T
            log_ratio = ((oldb - zb) ** 2 - (mean - zb) ** 2).sum(axis=1) / (2 * sigma2)
            ratio = np.exp(np.clip(log_ratio, -30, 30))
            active = np.where(((advb >= 0) & (ratio <= 1 + clip_ratio)) |
                              ((advb < 0) & (ratio >= 1 - clip_ratio)), 1.0, 0.0)
            coeff = active * advb * ratio / sigma2
            grad = (coeff[:, None, None] * (zb - mean)[:, :, None] * xb[:, None, :]).mean(axis=0)
            w += learning_rate * grad
    return w.tolist()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, help='new directory for training state and rollout logs')
    p.add_argument('--anchor', default='/workspace/shared/candidates_wip/es1_g1/params.json')
    p.add_argument('--seeds', nargs='+', type=int, required=True)
    p.add_argument('--updates', type=int, default=1)
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--noise-std', type=float, default=.04)
    p.add_argument('--learning-rate', type=float, default=.0002)
    p.add_argument('--epochs', type=int, default=2)
    p.add_argument('--timeout', type=float, default=180)
    p.add_argument('--opponents', nargs='+', default=list(PANEL))
    a = p.parse_args()
    if not 1 <= a.workers <= 20 or a.updates < 1 or a.noise_std <= 0:
        p.error('workers must be 1..20; updates and noise-std must be positive')
    unknown = set(a.opponents) - set(PANEL)
    if unknown:
        p.error(f'unknown opponents: {sorted(unknown)}')
    if len(a.seeds) != len(set(a.seeds)):
        p.error('duplicate seeds')
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    anchor = base_params(); anchor.update(load_json(a.anchor))
    weights = zero_weights()
    state = dict(anchor=a.anchor, anchor_params=anchor, weights=weights, config=vars(a), history=[])
    for iteration in range(a.updates):
        rollout_dir, rows, samples, info = rollout(out, weights, anchor, a.seeds, {k:PANEL[k] for k in a.opponents},
                                                    a.noise_std, a.workers, a.timeout, iteration)
        if 'error' in info:
            state['history'].append({**info, 'run_dir': str(rollout_dir)})
            (out/'state.json').write_text(json.dumps(state, indent=2)); raise RuntimeError(info['error'])
        weights = ppo_update(weights, samples, a.noise_std, a.learning_rate, .2, a.epochs, iteration)
        state['weights'] = weights
        state['history'].append({**info, 'run_dir': str(rollout_dir)})
        (out/'state.json').write_text(json.dumps(state, indent=2))
    make_daily_agent_file(weights, out/'candidate'/'main.py', anchor=anchor)
    print(json.dumps(state['history'][-1], indent=2))


if __name__ == '__main__':
    main()
