"""T025 diagnostic wrapper: c3g5 with only v9/2-Q horizon reset to es3."""
from pathlib import Path

_src = Path('/workspace/shared/candidates_wip/es4_c3g5/main.py').read_text()
_old = '"_V92_Q_H": 65'
_new = '"_V92_Q_H": 62'
assert _old in _src
exec(compile(_src.replace(_old, _new), '/workspace/shared/candidates_wip/es4_c3g5/main.py', 'exec'))
