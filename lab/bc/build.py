"""Build BC dataset from replays. usage: python build.py --team "DSM" --glob '/workspace/shared/replays/team_16732748/*.gz' --out /workspace/shared/bc_data/dsm --workers 16"""
import argparse, copy, glob, gzip, json, os, sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feat

def obs_at(d, t, p):
    o = copy.deepcopy(d["steps"][t][p]["observation"]); sh = d["steps"][t][0]["observation"]
    for k in ("step", "day", "hour", "farms", "market", "town"):
        if k not in o and k in sh: o[k] = sh[k]
    o["player"] = p; return o


def encode_episode(d, p, dst):
    """Encode player p of an episode dict {steps, rewards, ...} into a BC .npz (same schema as build.one)."""
    T = len(d["steps"]) - 1
    B = np.zeros((T, feat.C_BOARD, 10, 10), np.float16); ui = []; G = np.zeros((T, feat.G_DIM), np.float32)
    Q = np.zeros((T, len(feat.MKT_KEYS)), np.int16); ut, ux, uy, uv, ua = [], [], [], [], []
    for t in range(T):
        o = obs_at(d, t, p); a = d["steps"][t + 1][p]["action"] or {}
        B[t] = feat.board_tensor(o, p); G[t] = feat.glob_vec(o, p); Q[t] = feat.encode_market(a.get("market"))
        acts = [a.get("farmer")] + list(a.get("hands") or [])
        for i, (x, y, vec) in enumerate(feat.unit_list(o, p)):
            ut.append(t); ux.append(x); uy.append(y); uv.append(vec); ui.append(i)
            ua.append(feat.encode_unit_action(acts[i] if i < len(acts) else None))
    # target cell = where this unit does its next non-move action within the same day
    MOVES = {feat.UNIT_IDX[k] for k in ("NORTH", "SOUTH", "EAST", "WEST")}
    ut_a = np.array(ut); ui_a = np.array(ui); ux_a = np.array(ux); uy_a = np.array(uy); ua_a = np.array(ua)
    key = {(int(t_), int(i_)): k for k, (t_, i_) in enumerate(zip(ut_a, ui_a))}
    tx = ux_a.copy(); ty = uy_a.copy()
    for k in range(len(ut_a)):
        if ua_a[k] not in MOVES: continue
        t_, i_ = int(ut_a[k]), int(ui_a[k]); day = t_ // 24; j = k
        while True:
            nk = key.get((t_ + 1, i_))
            if nk is None or (t_ + 1) // 24 != day: break
            t_ += 1; j = nk
            if ua_a[j] not in MOVES: break
        tx[k], ty[k] = ux_a[j], uy_a[j]
    r = d["rewards"]
    np.savez_compressed(dst, B=B, G=G, Q=Q, ut=np.array(ut, np.int32), ux=np.array(ux, np.int8), uy=np.array(uy, np.int8),
                        uv=np.array(uv, np.float32), ua=np.array(ua, np.int16), tx=tx.astype(np.int8), ty=ty.astype(np.int8), ui=ui_a.astype(np.int8), won=np.array(r[p] > r[1 - p]), margin=np.array(r[p] - r[1 - p]))


def one(args):
    f, team, out = args
    dst = f"{out}/{os.path.basename(f).split('-replay')[0]}.npz"
    if os.path.exists(dst): return "skip"
    try:
        d = json.load(gzip.open(f, "rt") if f.endswith(".gz") else open(f))
        names = d["info"].get("TeamNames", [])
        if team not in names: return "noteam"
        encode_episode(d, names.index(team), dst)
        return "ok"
    except Exception as e:
        return f"ERR {f}: {e!r}"

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--team"); ap.add_argument("--glob"); ap.add_argument("--out"); ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    fs = sorted(glob.glob(a.glob))
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(one, [(f, a.team, a.out) for f in fs]))
    from collections import Counter
    print(Counter(r.split(" ")[0] for r in res)); [print(r) for r in res if r.startswith("ERR")][:5]
