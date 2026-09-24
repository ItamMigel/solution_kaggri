"""One traceable official-engine PPO rollout per process.

This deliberately passes Python callables to ``Environment.run``.  Kaggle
Environments accepts callables locally; that lets the worker read the optional
training trace kept in the candidate source namespace.  The final exported
agent remains an ordinary self-contained source file and is evaluated through
compare.py.
"""
import contextlib
import io
import json
from pathlib import Path
import sys
import traceback


def load_agent(path, policy_seed=None):
    path = Path(path).resolve()
    namespace = {'__file__': str(path), '__name__': '__kaggriculture_agent__'}
    exec(compile(path.read_text(), str(path), 'exec'), namespace)
    if policy_seed is not None and '_T017_RNG' in namespace:
        namespace['_T017_RNG'].seed(int(policy_seed) % 2**32)
    return namespace['agent'], namespace


def run(job):
    from kaggle_environments import make
    candidate, candidate_ns = load_agent(job['candidate_path'], job.get('policy_seed'))
    opponent, _ = load_agent(job['opponent_path'])
    agents = [candidate, opponent]
    if job['seat']:
        agents.reverse()
    env = make('kaggriculture', configuration={'seed': job['seed']}, debug=False)
    env.run(agents)
    status = [state.status for state in env.state]
    rewards = [state.reward for state in env.state]
    trace = candidate_ns.get('_T017_TRACE', [])
    invalid = [dict(step=step, seat=seat, status=state.status)
               for step, pair in enumerate(env.steps[1:], 1)
               for seat, state in enumerate(pair)
               if state.status in ('ERROR', 'INVALID', 'TIMEOUT') or not isinstance(state.action, dict)]
    result = {key: job[key] for key in ('kind', 'seed', 'seat', 'opponent')}
    result.update(status=status, rewards=rewards, trace=trace)
    if invalid or status != ['DONE', 'DONE'] or any(x is None for x in rewards):
        result['error'] = 'game did not complete normally'
        result['invalid_steps'] = invalid[:8]
    else:
        result['margin'] = rewards[job['seat']] - rewards[1 - job['seat']]
        result['points'] = 1.0 if result['margin'] > 0 else .5 if result['margin'] == 0 else 0.0
        if job['kind'] == 'policy' and len(trace) != 30:
            result['error'] = f'expected 30 daily policy records, got {len(trace)}'
    return result


if __name__ == '__main__':
    job = json.loads(sys.stdin.read())
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            result = run(job)
    except Exception:
        result = {key: job[key] for key in ('kind', 'seed', 'seat', 'opponent')}
        result.update(error='worker exception', detail=traceback.format_exc()[-4000:])
    if 'error' in result:
        result['process_output'] = captured.getvalue()[-2000:]
    print(json.dumps(result))
