"""Focused port checks: actual HG source, loader selection, mixture identity."""
import os
for k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[k] = '1'
import ast
import contextlib
import copy
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    # Reuse the reviewed terminal engine fixtures, writing only into T047.
    import sys
    sys.path.insert(0, str(HERE.parent/'t045/execution'))
    import fixtures
    fixtures.build.HERE = HERE
    # build_source reads terminal.py from HERE; restore lookup around its call.
    old_build = fixtures.build.build_source
    def build_source(*args):
        fixtures.build.HERE = HERE.parent/'t045/execution'
        try:
            return old_build(*args)
        finally:
            fixtures.build.HERE = HERE
    fixtures.build.build_source = build_source
    fixtures.main()
    results = json.loads((HERE/'fixtures.json').read_text())
    hgmods = {}
    for v in ('m26','a1'):
        src = (HERE/'exports'/v/'main.py').read_text()
        hgmods[v] = {'agent': lambda o,c=None: {}}
        exec(src[src.index('# ================= HG:'):], hgmods[v])
    tiles = [[None]*10 for _ in range(10)]
    for x in (4,5):
        tiles[4][x] = {'kind':'PASTURE','animal':'COW','consecutive_unfed':1,'fed_today':False}
    obs = {'player':0,'step':23,'farms':[{'tiles':tiles,'farmer':[4,4],'hands':[],'money':0}],
           'private':{'shed':{},'inventories':[{'WHEAT':2}]},'market':{'prices':{'WHEAT':30}}}
    act = {'farmer':['FEED'],'hands':[],'market':[]}
    assert hgmods['m26']['_hg_apply'](obs,copy.deepcopy(act))['farmer'] == ['EAST']
    assert hgmods['a1']['_hg_apply'](obs,copy.deepcopy(act))['farmer'] == ['FEED']
    from kaggle_environments.agent import get_last_callable
    for v in ('m26','terminal','a1','dsm75_mg25'):
        path = HERE/'exports'/v/'main.py'
        selected = get_last_callable(path.read_text(), path=str(path))
        assert selected.__name__ == 'agent'
        assert selected.__code__.co_firstlineno == max(n.lineno for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name=='agent')
        if v == 'dsm75_mg25':
            model = selected.__globals__['_AG'].model
            assert list(model.w) == [.375,.375,.125,.125]
            assert len(model.m) == 4
            for i in (0,1):
                assert model.m[i].W is model.m[i+2].W
                assert model.m[i].cfg['teams'][model.m[i].tv.argmax()] == 'o28_dsm_cn'
                assert model.m[i+2].cfg['teams'][model.m[i+2].tv.argmax()] == 'mgoose_cn'
    results.update(m26_a1_fixture='PASS', actual_export_loader_selection='PASS', mixture_weights_and_tv='PASS')
    (HERE/'fixtures.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results))


if __name__ == '__main__':
    main()
