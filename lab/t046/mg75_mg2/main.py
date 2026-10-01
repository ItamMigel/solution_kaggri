"""LOCAL RESEARCH ONLY: frozen m15 two-checkpoint MG75/MG2-25 + original HG d13.

Requires the local original export and lab/t046/team_screen.py. Not a portable
candidate or submission archive. Fail-fast deliberately exposes experiment errors.
"""
import sys
sys.dont_write_bytecode = True
from collections import Counter
import hashlib

sys.path.insert(0, '/workspace/wt/codex/lab/t046')
from team_screen import BASE, load, configure

_BASE_SHA256 = hashlib.sha256(BASE.read_bytes()).hexdigest()
assert _BASE_SHA256 == '1b1261f65cc365fbff76578965de712e7398b7819d80fe6ef3113c272ea0bfe6', "Frozen parent hash changed"
_COUNTS = Counter()
_MOD = load(BASE)
configure(_MOD, 'mg75_mg2', _COUNTS)


def agent(obs, config=None):
    return _MOD._hg_apply(obs, _MOD._AG(obs, config))


agent.telemetry = _COUNTS
