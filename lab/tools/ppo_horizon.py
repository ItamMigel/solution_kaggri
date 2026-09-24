"""Self-contained daily knob-policy wrapper for Horizon v5.

The policy is deliberately dependency-free after export: it appends its weights and
a small feature extractor to the submission source.  Zero weights are an exact
no-op, which makes the PPO anchor directly comparable with ``v5_market``.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from knobs import SPACE, base_params

NAMES = tuple(SPACE)
# day, own/other cash, hands, quadrants, unlocked shops, shed load, mean price,
# and a bias.  All are bounded before the policy sees them.
FEATURES = 8


def zero_weights():
    """Return the linear Gaussian-policy mean at the exact Horizon base."""
    return [[0.0] * (FEATURES + 1) for _ in NAMES]


def _validate(weights):
    if len(weights) != len(NAMES) or any(len(row) != FEATURES + 1 for row in weights):
        raise ValueError(f"expected {len(NAMES)}x{FEATURES + 1} policy weights")
    return [[float(x) for x in row] for row in weights]


def make_daily_agent_file(weights, out, *, base_path=None, scale=1.0, anchor=None):
    """Write a loadable agent that updates all knobs once per simulated day."""
    weights = _validate(weights)
    if base_path is None:
        base_path = Path(__file__).resolve().parents[2] / "agents" / "horizon_v5_market.py"
    source = Path(base_path).read_text().rstrip() + "\n"
    anchor_params = base_params()
    if anchor is not None:
        anchor_params.update({name: float(anchor[name]) for name in NAMES if name in anchor})
    payload = dict(names=NAMES, base=anchor_params, space=SPACE, weights=weights,
                   scale=float(scale), features=FEATURES)
    source += "\n# --- T017 daily PPO knob policy; self-contained ---\n"
    source += "_T017=" + json.dumps(payload, separators=(",", ":")) + "\n"
    source += r'''
_T017_PARENT = agent
_T017_DAY = {}
def _t017_clip(v, lo, hi, kind):
    v = min(float(hi), max(float(lo), float(v)))
    return int(round(v)) if kind == 'int' else float(v)
def _t017_features(obs):
    player = int(obs.get('player', 0)); farms = obs.get('farms') or []
    own = farms[player] if player < len(farms) else {}
    other = farms[1-player] if len(farms) > 1-player else {}
    private = obs.get('private') or {}; market = obs.get('market') or {}
    prices = market.get('prices') or {}; shops = (obs.get('town') or {}).get('unlocked_shops') or []
    shed = private.get('shed') or {}
    mean_price = sum(float(v) for v in prices.values()) / max(1, len(prices))
    return [min(1., max(0., float(obs.get('step', 0))/720.)),
            min(3., max(-3., float(own.get('money', 0))/10000.)),
            min(3., max(-3., float(other.get('money', 0))/10000.)),
            min(1., len(own.get('hands') or []) / 16.),
            min(1., len(own.get('unlocked_quadrants') or []) / 4.),
            min(1., len(shops) / 8.), min(1., sum(float(v) for v in shed.values()) / 100.),
            min(3., max(0., mean_price / 100.))]
def _t017_set(obs):
    step = int(obs.get('step', 0)); player = int(obs.get('player', 0)); day = step // 24
    if _T017_DAY.get(player) == day: return
    _T017_DAY[player] = day; x = _t017_features(obs) + [1.0]
    for name, row in zip(_T017['names'], _T017['weights']):
        raw = sum(a*b for a,b in zip(row, x)) * _T017['scale']
        _, lo, hi, kind = _T017['space'][name]
        base = _T017['base'][name]
        globals()[name] = _t017_clip(base + (hi-lo) * raw / (1.0 + abs(raw)) / 2., lo, hi, kind)
def t017_daily_agent(obs, configuration=None):
    _t017_set(obs)
    return _T017_PARENT(obs, configuration)
agent = t017_daily_agent
'''
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(source)
    return out
