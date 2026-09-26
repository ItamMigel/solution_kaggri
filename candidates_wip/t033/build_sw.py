"""T033: es7_wm + opponent-class switch. When Horizon's own clone detector (_RACE_STATE[p]['horizon']>0, i.e. rival on our route
tape with >=95% similarity, steps 216..695) fires on >= SW_VOTES turns, switch the 24 knobs to an anti-Horizon set for the rest
of the game. Otherwise the agent is byte-identical in behaviour to es7_wm.
usage: python build_sw.py <alt_params.json|main.py with knob line> <out/main.py>"""
import json, sys
BASE = "/workspace/shared/candidates/es7_wm/pkg/main.py"
def knob_line(path):
    if path.endswith(".json"): return json.load(open(path))
    lines = [l for l in open(path).read().splitlines() if l.startswith('globals().update({"_ADV_LOOK"')]
    return json.loads(lines[-1][len("globals().update("):-1])
alt = knob_line(sys.argv[1]); out = sys.argv[2]; votes = int(sys.argv[3]) if len(sys.argv) > 3 else 6
src = open(BASE).read()
wrap = f'''

# ---- T033 opponent-class switch (Claude) -------------------------------------------------------------
_SW_PARENT = agent
_SW_ALT = {json.dumps(alt)}
_SW_BASE = {{k: globals()[k] for k in _SW_ALT if k in globals()}}
_SW_VOTES = {votes}
_SW_STATE = {{}}
_SW_REPORT = dict(sw_on=0, sw_step=-1, sw_votes=0, sw_errors=0)
del agent
def agent(observation, configuration=None):
    try:
        p = int(observation["player"]); step = int(observation["step"])
        st = _SW_STATE.get(p)
        if st is None or step <= st["step"]:
            st = _SW_STATE[p] = {{"step": -1, "on": False, "votes": 0}}
            globals().update(_SW_BASE); _SW_REPORT.update(sw_on=0, sw_step=-1, sw_votes=0)
        st["step"] = step
    except Exception:
        _SW_REPORT["sw_errors"] += 1; st = None
    action = _SW_PARENT(observation, configuration)
    try:
        if st is not None and not st["on"]:
            rs = _RACE_STATE.get(p) or {{}}
            if rs.get("horizon", 0) > 0:
                st["votes"] += 1; _SW_REPORT["sw_votes"] = st["votes"]
                if st["votes"] >= _SW_VOTES:
                    st["on"] = True; globals().update(_SW_ALT); _SW_REPORT.update(sw_on=1, sw_step=step)
    except Exception:
        _SW_REPORT["sw_errors"] += 1
    return action
agent.telemetry = _SW_REPORT
'''
import os; os.makedirs(os.path.dirname(out) or ".", exist_ok=True); open(out, "w").write(src + wrap)
print(out, "alt knobs", len(alt))
