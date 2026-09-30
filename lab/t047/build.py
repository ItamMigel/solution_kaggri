"""Single-change m26 exports; original weights and fallback behavior retained."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 't045/execution'))
from build import unit_engine_source

BASE = Path('/workspace/shared/research/t046_ft/agents/m26dsm/main.py')

MIXTURE = '''
class _T047Weighted(_Ens):
    def __init__(self, members):
        import copy
        extra = [copy.copy(x) for x in members]
        for x in extra:
            assert 'mgoose_cn' in x.cfg['teams']
            x.tv = _team_vec(x.cfg, 'mgoose_cn')
        super().__init__(members + extra)
        self.w = np.array([.75 / len(members)] * len(members) + [.25 / len(members)] * len(members), dtype=np.float32)

    def mix(self, xs):
        return np.einsum('m,m...->...', self.w, np.stack(xs))

    def units(self, hs, G, ux, uy, uv):
        outs = [x.units(h, G, ux, uy, uv) for x, h in zip(self.m, hs)]
        return self.mix([o[0] for o in outs]), self.mix([o[1] for o in outs]), [o[2] for o in outs]

    def qty(self, zs, i, cls):
        return self.mix([x.qty(z, i, cls) for x, z in zip(self.m, zs)])

    def m_step(self, sts, prev_t, prev_q, sl):
        outs = [x.m_step(st, prev_t, prev_q, sl) for x, st in zip(self.m, sts)]
        return [o[0] for o in outs], self.mix([o[1] for o in outs])

    def m_qty(self, sts, tok):
        return self.mix([x.m_qty(st, tok) for x, st in zip(self.m, sts)])

_AG.model = _T047Weighted(_AG.model.m)
'''


def main():
    source = BASE.read_text()
    exports = {'m26': source}
    a1 = source
    for old, new in [
        ('    urgent = list(urgent_all)\n', '    urgent = list(urgent_all)\n    protected = set()\n'),
        ('            urgent.remove(pos[i]); carried[i] -= 1\n', '            urgent.remove(pos[i]); carried[i] -= 1\n            protected.add(i)\n'),
        ('    free = set(range(len(pos)))\n', '    free = set(range(len(pos))) - protected\n'),
    ]:
        assert a1.count(old) == 1
        a1 = a1.replace(old, new)
    exports['a1'] = a1
    marker = "_AG = Agent(None, **{'fill': True, 'team': 'o28_dsm_cn'})\n"
    assert source.count(marker) == 1
    exports['dsm75_mg25'] = source.replace(marker, marker + MIXTURE)
    terminal = (HERE.parent / 't045/execution/terminal.py').read_text()
    exports['terminal'] = source + '\n_T047_ENGINE = {}\nexec(' + repr(unit_engine_source()) + ', _T047_ENGINE)\n_T047_TERM = {}\nexec(' + repr(terminal) + ''', _T047_TERM)
_T047_ERRORS = {'terminal': 0}
_T047_PARENT = agent
del agent
def agent(obs, config=None):
    action = _T047_PARENT(obs, config)
    try:
        return _T047_TERM['liquidate'](obs, action, config, _T047_ENGINE, True)
    except Exception:
        _T047_ERRORS['terminal'] += 1
        return action
'''
    manifest = {'base': str(BASE), 'exports': {}}
    for name, src in exports.items():
        target = HERE / 'exports' / name / 'main.py'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(src)
        compile(src, str(target), 'exec')
        manifest['exports'][name] = {'path': str(target), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    assert (HERE/'exports/m26/main.py').read_bytes() == BASE.read_bytes()
    (HERE/'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
