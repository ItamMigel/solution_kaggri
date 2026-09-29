"""Test the extra NOOP deletion used by build3 after verified canonicalization."""
import contextlib
import copy
import gzip
import io
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, '/workspace/shared/pavel_lab/lab/pavel')
from canon_market import simulate


def one(arg):
    episode, seat = arg
    root = Path('/workspace/shared/research')
    d = json.load(gzip.open(root / f't045_replays/episode-{episode}-replay.json.gz', 'rt'))
    c = json.loads((root / f't045_canonical/episode-{episode}.json').read_text())
    tape = copy.deepcopy(c['canon'])
    for i, orders in enumerate(tape[seat]):
        tape[seat][i] = [x for x in orders if x != ['NOOP']]
    env, _, _ = simulate(d, market_override=tape)
    rewards = [s.reward for s in env.state]
    return dict(episode=episode, seat=seat, name=c['names'][seat],
                before=d['rewards'], after=rewards, exact=rewards == d['rewards'])


if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(one, [(115344920, 0), (115344920, 1), (115343521, 0), (115343521, 1)]))
    Path('/workspace/shared/research/t045_nonoop_audit.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows, indent=2))
