"""T025 diagnostic wrapper: c3g5 with only v9/2-Q scoring reset to es3."""
from pathlib import Path

_src = Path('/workspace/shared/candidates_wip/es4_c3g5/main.py').read_text()
_old = '"_V92_Q_PF": 0.8495866104306726, "_V92_Q_PM": 0.723951467162242'
_new = '"_V92_Q_PF": 0.9125082883622124, "_V92_Q_PM": 0.6341685864297154'
assert _old in _src
exec(compile(_src.replace(_old, _new), '/workspace/shared/candidates_wip/es4_c3g5/main.py', 'exec'))
