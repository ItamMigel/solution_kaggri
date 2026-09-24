"""Build self-contained tape agents. usage: python mk_tape_agents.py <index.jsonl> <team name> <sub_id|all> <outdir> [--won-only]"""
import base64, json, os, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tapes import load, tapes_of
TPL = '''import base64, json, zlib
_T = json.loads(zlib.decompress(base64.b85decode({blob!r})))
def agent(obs, config=None):
    s = int(obs["step"])
    return _T[s] if s < len(_T) else {{"farmer": ["PASS"], "hands": [], "market": []}}
'''
idx, team, sub, out = sys.argv[1:5]; won = "--won-only" in sys.argv
n = 0
for l in open(idx):
    r = json.loads(l)
    if sub != "all" and str(r["sub_id"]) != sub: continue
    try: d = load(r["file"])
    except Exception: continue
    for t in tapes_of(d):
        if t["name"] != team or (won and t["reward"] <= t["opp_reward"]): continue
        dd = f"{out}/ep{r['episode_id']}"; os.makedirs(dd, exist_ok=True)
        blob = base64.b85encode(zlib.compress(json.dumps(t["tape"], separators=(",", ":")).encode(), 9)).decode()
        open(dd + "/main.py", "w").write(TPL.format(blob=blob))
        json.dump({k: t[k] for k in ("name", "reward", "opp_reward", "shops144")}, open(dd + "/meta.json", "w")); n += 1
print(n, "tape agents ->", out)
