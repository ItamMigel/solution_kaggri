"""Local-only, paired comparison against frozen Horizon agents.

Every game runs in a new Python process using Kaggle's official Environment.run.
No Kaggle credentials, uploads, account access, or submission commands are used.
"""
import argparse
import concurrent.futures
import hashlib
import importlib.metadata
import json
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent
BASELINES = {'v3': ROOT/'agents/horizon_v3.py',
             'v4_8turn': ROOT/'agents/horizon_v4_8turn.py',
             'v4_12turn': ROOT/'agents/horizon_v4.py',
             'v5_market': ROOT/'agents/horizon_v5_market.py',
             'v5_guarded': ROOT/'agents/horizon_v5_guarded.py'}
DEFAULT_BASELINES = ['v3', 'v4_8turn', 'v4_12turn']


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def parse_agent(value):
    if '=' in value:
        name, path = value.split('=', 1)
    else:
        path = value; name = pathlib.Path(path).stem
    if not name or not all(c.isalnum() or c in '_-' for c in name):
        raise ValueError('Agent names may contain letters, digits, underscore and hyphen')
    path = pathlib.Path(path).expanduser().resolve()
    if path.is_dir():
        path = path/'main.py'
    if path.suffix != '.py' or not path.is_file():
        raise ValueError(f'Expected an existing .py file or folder containing main.py: {path}')
    return name, str(path)


def verify_kit():
    manifest = json.loads((ROOT/'MANIFEST.json').read_text())
    for path, digest in manifest['files'].items():
        if sha(ROOT/path) != digest:
            raise ValueError(f'Kit file changed: {path}')
    return manifest


def run_job(job, timeout):
    base = {k: job[k] for k in ('candidate', 'opponent', 'seed', 'seat')}
    started = time.perf_counter()
    try:
        proc = subprocess.run([sys.executable, str(ROOT/'game_worker.py')],
                              input=json.dumps(job), text=True, capture_output=True,
                              timeout=timeout, cwd=str(pathlib.Path(job['candidate_path']).parent))
        if proc.returncode:
            return dict(**base, error='worker_process_failed',
                        detail=(proc.stderr or proc.stdout)[-4000:], returncode=proc.returncode)
        result = json.loads(proc.stdout)
        if any(result.get(k) != v for k, v in base.items()):
            raise ValueError('Worker result identity differs from requested game')
        result['seconds'] = time.perf_counter()-started
        return result
    except subprocess.TimeoutExpired:
        return dict(**base, error='wall_timeout', timeout_seconds=timeout)
    except Exception as exc:
        return dict(**base, error=repr(exc))


def write_readme(out, summary, count, worlds):
    lines = ['# Local comparison results',
        f'{count} games requested on {worlds} world seeds; both seats. No submissions were made.',
        'All rates below are from the candidate agent’s perspective. Confidence intervals resample whole world seeds, including both seats and all opponents. They condition on this fixed suite.',
        '| Candidate | Opponent | W / D / L | Errors | Score rate | 95% world interval | Mean margin | Worst 10% mean | Worst margin |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for name, r in summary['candidates'].items():
        for opponent, m in r['by_opponent'].items():
            if 'score_rate' not in m:
                lines.append(f"| {name} | {opponent} | — | {m['errors']} | — | — | — | — | — |")
                continue
            lo, hi = m['world_block_score_95']
            lines.append(f"| {name} | {opponent} | {m['wins']} / {m['draws']} / {m['losses']} | {m['errors']} | {100*m['score_rate']:.1f}% | [{100*lo:.1f}, {100*hi:.1f}]% | {m['mean_margin']:+.1f} | {m['worst_decile_mean_margin']:+.1f} | {m['worst_margin']:+.0f} |")
    text = '\n\n'.join(lines[:3])+'\n\n'+'\n'.join(lines[3:])
    if not summary['evaluation_valid']:
        text += '\n\n**INVALID for promotion: at least one game failed or an input changed. Inspect games.jsonl; do not silently discard failures.**'
    text += '\n\n`summary.json` includes per-seat results, severe-loss counts, worst games and paired comparisons between your candidates. A 100% observed score is not certainty. Identical policies can still have seat effects. Repeated use of a seed panel turns it into development evidence.\n'
    (out/'README.md').write_text(text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--agent', action='append', default=[], metavar='NAME=FILE.py',
                   help='Repeat to compare two or more friend candidates on the same opponents/seeds')
    p.add_argument('--baselines', nargs='+', choices=sorted(BASELINES), default=list(DEFAULT_BASELINES))
    p.add_argument('--opponent', action='append', default=[], metavar='NAME=FILE.py',
                   help='Optional additional reacting opponents')
    seeds = p.add_mutually_exclusive_group()
    seeds.add_argument('--seeds-file', default=str(ROOT/'seeds/development.json'))
    seeds.add_argument('--seeds', nargs='+', type=int)
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--game-timeout', type=float, default=180,
                   help='Hard wall-clock limit per isolated game, including imports')
    p.add_argument('--asset', action='append', default=[],
                   help='Additional helper/weight file to hash before and after the run; repeat as needed')
    p.add_argument('--decision-note', default='Win rate first; inspect every opponent, both seats, severe losses and runtime. No automatic promotion.',
                   help='Freeze your selection criteria in the run manifest before confirmation')
    p.add_argument('--save-replays', action='store_true', help='Large: about 20–35 MB per game')
    p.add_argument('--out', help='New output directory; an existing directory is never overwritten')
    p.add_argument('--verify-only', action='store_true')
    a = p.parse_args()
    verify_kit()
    if a.verify_only:
        print('All kit file hashes match MANIFEST.json.'); return 0
    if not a.agent or not a.out:
        p.error('--agent and --out are required for an evaluation')
    if a.workers < 1 or a.game_timeout <= 0:
        p.error('workers and game-timeout must be positive')
    candidates = dict(parse_agent(v) for v in a.agent)
    if len(candidates) != len(a.agent):
        p.error('Duplicate candidate names')
    opponents = {k: str(BASELINES[k]) for k in a.baselines}
    for value in a.opponent:
        name, path = parse_agent(value)
        if name in opponents:
            p.error(f'Duplicate opponent name: {name}')
        opponents[name] = path
    if a.seeds is None:
        seed_data = json.loads(pathlib.Path(a.seeds_file).read_text())
        world_seeds = seed_data['seeds'] if isinstance(seed_data, dict) else seed_data
    else:
        world_seeds = a.seeds
    if not world_seeds or any(type(s) is not int or not 0 <= s < 2**31 for s in world_seeds):
        p.error('Seeds must be nonempty integers in [0, 2**31)')
    if len(world_seeds) != len(set(world_seeds)):
        p.error('Duplicate seeds would inflate evidence')
    actual_version = importlib.metadata.version('kaggle-environments')
    if actual_version != '1.32.7':
        raise RuntimeError(f'Expected kaggle-environments==1.32.7; found {actual_version}')
    inputs = {*candidates.values(), *opponents.values(), str(ROOT/'compare.py'),
              str(ROOT/'game_worker.py'), str(ROOT/'stability_report.py'),
              *(str(pathlib.Path(v).expanduser().resolve()) for v in a.asset)}
    before = {path: sha(path) for path in sorted(inputs)}
    out = pathlib.Path(a.out).expanduser().resolve(); out.mkdir(parents=True, exist_ok=False)
    if a.save_replays:
        (out/'replays').mkdir()
    jobs = []
    for seed in world_seeds:
        for opponent, opponent_path in opponents.items():
            for name, path in candidates.items():
                for seat in (0, 1):
                    jobs.append(dict(candidate=name, candidate_path=path, opponent=opponent,
                        opponent_path=opponent_path, seed=seed, seat=seat,
                        replay_path=str(out/'replays'/f'{len(jobs):06d}.json') if a.save_replays else None))
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidates=candidates, opponents=opponents, seeds=world_seeds, expected_games=len(jobs),
        input_sha256=before, python=sys.version, kaggle_environments=actual_version,
        runner='Official make(...).run([...]), new subprocess per game',
        game_timeout=a.game_timeout, workers=a.workers,
        decision_note=a.decision_note,
        extra_assets=a.asset, all_self_matchups=[(n,o) for n,path in candidates.items()
            for o,opp in opponents.items() if before[path] == before[opp]])
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'Frozen {len(jobs)} games, {len(world_seeds)} worlds, both seats. Output: {out}', flush=True)
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool, (out/'games.jsonl').open('x') as log:
        futures = [pool.submit(run_job, job, a.game_timeout) for job in jobs]
        for i, future in enumerate(futures, 1):
            row = future.result(); rows.append(row); log.write(json.dumps(row)+'\n'); log.flush()
            if i % 12 == 0 or i == len(jobs):
                print(f'{i}/{len(jobs)} completed; errors={sum("error" in r for r in rows)}', flush=True)
    from stability_report import report
    result = report(rows, baseline=next(iter(candidates)))
    after = {path: sha(path) if pathlib.Path(path).is_file() else None for path in before}
    result.update(expected_games=len(jobs), completed_games=len(rows),
                  inputs_unchanged=before == after,
                  evaluation_valid=before == after and all('error' not in r for r in rows))
    (out/'summary.json').write_text(json.dumps(result, indent=2))
    write_readme(out, result, len(jobs), len(world_seeds))
    print(f'Results: {out / "README.md"}', flush=True)
    return 0 if result['evaluation_valid'] else 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, FileExistsError, FileNotFoundError) as exc:
        sys.exit(str(exc))
