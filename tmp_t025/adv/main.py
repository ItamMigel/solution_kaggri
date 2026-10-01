"""T025 diagnostic wrapper: c3g5 with sale-advance lookahead reset to es3."""
from pathlib import Path

_src = Path('/workspace/shared/candidates_wip/es4_c3g5/main.py').read_text()
_old = '"_ADV_LOOK": 18'
_new = '"_ADV_LOOK": 17'
assert _old in _src
exec(compile(_src.replace(_old, _new), '/workspace/shared/candidates_wip/es4_c3g5/main.py', 'exec'))
