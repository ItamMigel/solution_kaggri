"""T036 local-only phase probe: pull only Horizon's *third* land purchase forward.

The frozen controller already owns all worker routing.  This leaves its unit tape
untouched and changes only the legal BUY_LAND timing when two quadrants exist.
It is deliberately not a candidate and does not claim to reproduce the top
goose system.
"""

_BASE = "/workspace/shared/candidates/es7_wm/pkg/main.py"
exec(compile(open(_BASE, "rb").read(), _BASE, "exec"), globals(), globals())

_T036_PARENT_LAND = _hp_land
_T036_REPORT = {"attempts": 0, "changed": 0, "errors": 0}


def _hp_land(obs, action):
    """The base helper looks ahead in its active route; limit it to land #3."""
    try:
        player = int(obs["player"])
        quads = len(obs["farms"][player].get("unlocked_quadrants") or [])
        if quads != 2:
            return action
        _T036_REPORT["attempts"] += 1
        out = _T036_PARENT_LAND(obs, action)
        if out is not action:
            _T036_REPORT["changed"] += 1
        return out
    except Exception:
        _T036_REPORT["errors"] += 1
        return action


_HP["land_on"] = True
_HP["land_k"] = 24
_T036_BASE_AGENT = agent


def agent(obs, config=None):
    return _T036_BASE_AGENT(obs, config)


agent.telemetry = _T036_REPORT
