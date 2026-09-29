"""Build standalone variants only in this worktree; frozen source exports read-only."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('/workspace/shared/pavel_lab/lab/pavel')
ENGINE = Path('/workspace/solution_kaggri/.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py')
BASES = {k: ROOT / f'candidates/bc_hg_{k}_d13/main.py' for k in ('m15ens', 'mix4')}


def unit_engine_source():
    source = ENGINE.read_text()
    tree = ast.parse(source)
    defs = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            defs[node.name] = node
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defs[t.id] = node
    needed = set()
    todo = ['_apply_unit_action']
    while todo:
        name = todo.pop()
        if name in needed or name not in defs:
            continue
        needed.add(name)
        todo.extend(n.id for n in ast.walk(defs[name]) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load))
    nodes = sorted({defs[n] for n in needed}, key=lambda n: n.lineno)
    return '\n\n'.join(ast.get_source_segment(source, n) for n in nodes) + '\n'


def build_source(source, variant):
    assert variant in ('off', 'terminal', 'a1', 'a2')
    flags = dict(terminal=variant == 'terminal', a1=variant == 'a1', a2=variant == 'a2')
    # Only counted urgent, valid native FEEDs reserve their original worker.
    old = '    urgent = list(urgent_all)\n'
    assert source.count(old) == 1
    source = source.replace(old, old + '    protected = set()\n')
    old = '            urgent.remove(pos[i]); carried[i] -= 1\n'
    assert source.count(old) == 1
    source = source.replace(old, old + '            if _T045_FLAGS["a1"]: protected.add(i)\n')
    source = source.replace('    free = set(range(len(pos)))\n', '    free = set(range(len(pos))) - protected\n')
    old = '        cost, i = best\n'
    assert source.count(old) == 1
    source = source.replace(old, old + '        if _T045_FLAGS["a2"] and cost > 24 - hour:\n            continue\n')
    # Silent exception counters, no behavior change on successful calls.
    old = '    except Exception:\n        return {"farmer": ["PASS"], "hands": [], "market": []}\n'
    assert source.count(old) == 1
    source = source.replace(old, '    except Exception:\n        _T045_ERRORS["bc"] += 1\n        raise\n')
    # Fail loudly in new exports: do not turn defects into apparently valid games.
    old = '        _HG_STATS["errors"] += 1\n        return action\n'
    assert source.count(old) == 1
    source = source.replace(old, '        _HG_STATS["errors"] += 1\n        raise\n')
    terminal = (HERE / 'terminal.py').read_text()
    suffix = '\n\n_T045_FLAGS = ' + repr(flags) + '\n_T045_ERRORS = {"bc": 0, "terminal": 0}\n'
    suffix += '_T045_ENGINE = {}\nexec(' + repr(unit_engine_source()) + ', _T045_ENGINE)\n'
    suffix += '_T045_TERM = {}\nexec(' + repr(terminal) + ', _T045_TERM)\n'
    suffix += '''
_T045_PARENT = agent
del agent  # Kaggle file loader chooses the last inserted callable.
def agent(obs, config=None):
    action = _T045_PARENT(obs, config)
    try:
        return _T045_TERM['liquidate'](obs, action, config, _T045_ENGINE, _T045_FLAGS['terminal'])
    except Exception:
        _T045_ERRORS['terminal'] += 1
        raise
'''
    return source + suffix


def main():
    out = HERE / 'exports'
    out.mkdir(exist_ok=True)
    manifest = {'engine_sha256': hashlib.sha256(ENGINE.read_bytes()).hexdigest(), 'sources': {}, 'exports': {}}
    for base, path in BASES.items():
        data = path.read_bytes()
        manifest['sources'][base] = {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest()}
        for variant in ('off', 'terminal', 'a1', 'a2'):
            target = out / f'{base}_{variant}.py'
            target.write_text(build_source(data.decode(), variant))
            manifest['exports'][f'{base}_{variant}'] = {'path': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    (HERE / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    (HERE / 'unit_engine.py').write_text(unit_engine_source())
    print(json.dumps(manifest))

if __name__ == '__main__':
    main()
