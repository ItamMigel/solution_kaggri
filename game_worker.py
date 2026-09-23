"""One official local game per process; stdout contains exactly one JSON result."""
import contextlib
import io
import json
import pathlib
import random
import sys
import traceback


def run(job):
    from kaggle_environments import make
    import numpy as np
    # A reproducible policy RNG stream, distinct from the game's hidden RNG.
    # Torch/JAX policies should seed their own generators as well.
    policy_seed = (job['seed'] ^ 0x6D2B79F5) % 2**32
    random.seed(policy_seed); np.random.seed(policy_seed)
    paths = [job['candidate_path'], job['opponent_path']]
    if job['seat']:
        paths.reverse()
    env = make('kaggriculture', configuration={'seed': job['seed']}, debug=False)
    env.run(paths)
    status = [s.status for s in env.state]; rewards = [s.reward for s in env.state]
    calls = []; max_ms = []; diagnostics = []
    for seat in (0, 1):
        logs = [(step, pair[seat]) for step, pair in enumerate(env.logs)
                if len(pair) > seat and 'duration' in pair[seat]]
        calls.append(len(logs)); max_ms.append(max((r['duration']*1000 for _,r in logs), default=0.))
        diagnostics.extend(dict(step=step, seat=seat, stderr=r['stderr'][:2000])
                           for step,r in logs if r.get('stderr'))
    base = {k: job[k] for k in ('candidate', 'opponent', 'seed', 'seat')}
    # The game interpreter can overwrite a failure status with DONE on its last
    # turn. Inspect the whole trajectory too: valid schema-processed actions
    # are dictionaries; exceptions/timeouts/invalid actions leave action=None.
    invalid_steps = [dict(step=step, seat=seat, status=s.status)
                     for step, pair in enumerate(env.steps[1:], 1)
                     for seat, s in enumerate(pair)
                     if s.status in ('ERROR', 'INVALID', 'TIMEOUT')
                     or not isinstance(s.action, dict)]
    result = dict(**base, status=status, rewards=rewards, calls=calls, max_ms=max_ms,
                  shops=list(env.state[0].observation.town['unlocked_shops']),
                  diagnostics=diagnostics[:8], invalid_steps=invalid_steps[:8])
    if invalid_steps or status != ['DONE', 'DONE'] or any(v is None for v in rewards) or calls != [719, 719]:
        result['error'] = 'Game did not complete normally; inspect status and diagnostics'
    else:
        margin = rewards[job['seat']]-rewards[1-job['seat']]
        result.update(margin=margin, points=1. if margin > 0 else .5 if margin == 0 else 0.)
    if job.get('replay_path'):
        pathlib.Path(job['replay_path']).write_text(json.dumps(env.toJSON()))
        result['replay_path'] = job['replay_path']
    return result


if __name__ == '__main__':
    job = json.loads(sys.stdin.read())
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = run(job)
    except Exception:
        result = {k: job[k] for k in ('candidate', 'opponent', 'seed', 'seat')}
        result.update(error='worker_exception', detail=traceback.format_exc()[-4000:])
    if 'error' in result:
        result['process_output'] = captured.getvalue()[-2000:]
    print(json.dumps(result))
