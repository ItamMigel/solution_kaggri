"""T025 diagnostic wrapper: c3g5 with only v9/2-P horizon reset to es3."""
from pathlib import Path

_src = Path('/workspace/shared/candidates_wip/es4_c3g5/main.py').read_text()
_old = '"_V92_P_H": 61'
_new = '"_V92_P_H": 65'
assert _old in _src
exec(compile(_src.replace(_old, _new), '/workspace/shared/candidates_wip/es4_c3g5/main.py', 'exec'))
