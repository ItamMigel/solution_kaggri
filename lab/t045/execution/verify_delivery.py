"""Final read-only audit of coverage, runtime evidence, and frozen archive bytes."""
import hashlib
import json
import tarfile
from collections import Counter
from itertools import product
from pathlib import Path
import sys

run = Path(sys.argv[1])
evaluation_only = '--evaluation-only' in sys.argv
manifest = json.loads((run / 'manifest.json').read_text())
rows = [json.loads(line) for line in (run / 'games.jsonl').read_text().splitlines()]
key = lambda r: tuple(r[k] for k in ('base', 'variant', 'opp', 'seed', 'seat'))
expected = set(product(('m15ens', 'mix4'), ('off', 'a1', 'a2'), manifest['opponents'], manifest['seeds'], (0, 1)))
assert len(rows) == len(expected) == 3072
assert {key(r) for r in rows} == expected
lookup = {key(r): r for r in rows}
for r in rows:
    assert r['valid'] and r['status'] == ['DONE', 'DONE']
    assert r['counts']['calls'] == 719 and not any(r['errors'].values())
    assert r['counts'].get('host_alarm_fired', 0) == 0
    assert r['latency']['overage'] < 55
    if r['variant'] == 'off':
        assert r['terminal']['exact_baseline'] and r['counts']['shadow_calls'] == 719
    elif r.get('evaluation') == 'exact_identity_from_baseline':
        baseline = lookup[(r['base'], 'off', r['opp'], r['seed'], r['seat'])]
        assert baseline['counts']['shadow_calls'] == 719
        assert baseline['counts'].get('shadow_' + r['variant'] + '_changed_turns', 0) == 0
        assert r['rewards'] == baseline['rewards']
resource = json.loads((run / 'resource_continuation.json').read_text())
original = Path(resource['source_run']) / 'games.jsonl'
old_valid = [line for line in original.read_text().splitlines() if json.loads(line)['valid']]
assert (run / 'games.jsonl').read_text().splitlines()[:len(old_valid)] == old_valid
assert len(old_valid) == resource['adopted_valid_records'] == 780
for failed in resource['excluded_attempts']:
    replacement = lookup[key(failed)]
    assert replacement['valid'] and replacement['host_wall_limit_seconds'] == 3600
    assert not replacement['counts'].get('host_alarm_fired', 0)
engine=Path('/workspace/solution_kaggri/.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py')
assert hashlib.sha256(engine.read_bytes()).hexdigest()==manifest['exports']['engine_sha256']
for entry in manifest['exports']['exports'].values():
    assert hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest()==entry['sha256']
for entry in manifest['opponents'].values():
    assert hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest()==entry['sha256']
archives = {}
for base, variant in ([] if evaluation_only else product(('m15ens', 'mix4'), ('terminal', 'a1', 'a2'))):
    name = f't045_{base}_{variant}'
    folder = Path('/workspace/shared/candidates') / name
    meta = json.loads((folder / 'manifest.json').read_text())
    archive = folder / (name + '.tar.gz')
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == meta['archive_sha256']
    with tarfile.open(archive) as tar:
        assert tar.getnames() == ['main.py', 'ENGINE_LICENSE', 'NOTICE']
        digest = hashlib.sha256(tar.extractfile('main.py').read()).hexdigest()
    assert digest == meta['main_sha256'] == manifest['exports']['exports'][f'{base}_{variant}']['sha256']
    evidence = json.loads((folder / 'evidence.json').read_text())
    assert evidence['games'] == 512 and evidence['worlds'] == 32 and evidence['games_per_world'] == [16]
    assert all(v['games'] == 64 and v['games_per_world'] == [2] for v in evidence['opponents'].values())
    archives[name] = meta['archive_sha256']
result = dict(records=len(rows), errors=0, actual_methods=dict(Counter(r.get('evaluation', 'full_game') for r in rows)),
              terminal_branches=1024, paired_candidate_comparisons=3072, retained_valid_rows=len(old_valid),
              historical_infrastructure_attempts=len(resource['excluded_attempts']), all_retries_valid=True, archives=archives)
(run / ('evaluation_audit.json' if evaluation_only else 'delivery_audit.json')).write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
