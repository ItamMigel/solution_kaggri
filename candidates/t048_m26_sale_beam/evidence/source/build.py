"""Immutable-source bundles; off is the default in the reusable wrapper."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = Path('/workspace/shared/candidates/t047_m26_terminal/pkg/main.py')
ENGINE = Path('/workspace/solution_kaggri/.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py')

def source_closure(source, names):
    tree = ast.parse(source); defs = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            defs[node.name] = node
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defs[t.id] = node
    needed = set(); todo = list(names)
    while todo:
        name = todo.pop()
        if name in needed or name not in defs:
            continue
        needed.add(name)
        todo.extend(n.id for n in ast.walk(defs[name]) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load))
    return 'import math\n'+'\n\n'.join(ast.get_source_segment(source,n) for n in sorted({defs[n] for n in needed},key=lambda n:n.lineno))+'\n'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    engine = source_closure(ENGINE.read_text(), ['_process_market','SHOPS'])
    module = (HERE/'postprocess.py').read_text()
    base = BASE.read_text()
    manifest = {'base': {'path':str(BASE),'sha256':sha(BASE)}, 'engine_sha256':sha(ENGINE), 'exports':{}}
    (HERE/'market_engine.py').write_text(engine)
    for mode in ('off','sale_beam','late_ev'):
        suffix = '\n_T048_ENGINE = {}\nexec('+repr(engine)+', _T048_ENGINE)\n'
        suffix += '_T048_MOD = {}\nexec('+repr(module)+', _T048_MOD)\n'
        suffix += '_T048 = _T048_MOD["Postprocessor"](_T048_ENGINE, _T047_ENGINE, _T047_TERM, '+repr(mode)+')\n'
        suffix += '''_T048_PARENT = agent
del agent
def agent(obs, config=None):
    action = _T048_PARENT(obs, config)
    try:
        return _T048.apply(obs, action, config)
    except Exception:
        _T048.stats['errors'] += 1
        return action
'''
        target = HERE/'exports'/mode/'main.py'; target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(base+suffix); compile(base+suffix,str(target),'exec')
        manifest['exports'][mode] = {'path':str(target),'sha256':sha(target)}
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))

if __name__ == '__main__':
    main()
