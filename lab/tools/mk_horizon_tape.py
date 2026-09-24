"""Horizon chassis driven by an external whole-episode tape.
usage: python mk_horizon_tape.py <replay.json[.gz]> <team name> <out_main.py> [--base agents/horizon_v5_market.py] [--keep-endgame]
The tape becomes route 9001 and the router is pinned to it from step 0 (all Horizon repair/sale/final-day layers kept).
--keep-endgame: still switch to Horizon's shared endgame route 2 at step 648 (default: stay on the tape)."""
import argparse, base64, json, os, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tapes import load, tapes_of
ap = argparse.ArgumentParser(); ap.add_argument("replay"); ap.add_argument("team"); ap.add_argument("out")
ap.add_argument("--base", default="/workspace/wt/claude/agents/horizon_v5_market.py"); ap.add_argument("--keep-endgame", action="store_true")
a = ap.parse_args()
tape = [t for t in tapes_of(load(a.replay)) if t["name"] == a.team][0]["tape"]
blob = base64.b85encode(zlib.compress(json.dumps(tape, separators=(",", ":")).encode(), 9)).decode()
src = open(a.base).read()
anchor = "_IMPL=make_agent(_ROUTES,router=_router,**_SETTINGS)"
assert src.count(anchor) == 1
inject = f'''# --- T013 (claude): external tape pinned as route 9001 ---
_ROUTES[9001]=json.loads(zlib.decompress(base64.b85decode({blob!r})))
_T013_BASE_ROUTER=_router
def _router(observation,step,state):
    _T013_BASE_ROUTER(observation,step,state)
    {"return state.get('route',0) if step>=648 else 9001" if a.keep_endgame else "state['route']=9001; return 9001"}
'''
src = src.replace(anchor, inject + anchor)
open(a.out, "w").write(src); print("wrote", a.out, len(src) // 1000, "kB")
