"""Build BC v3 dataset from replays (one npz per episode, expert seat only).
usage: python build3.py --team Boey --glob '../../../../replays/56521745/*.gz' --out ../../../../bc3_data/boey --workers 24"""
import argparse, glob, gzip, json, os, sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feat3 as F  # noqa: E402

MOVES = {F.UNIT_IDX[k] for k in ("NORTH", "SOUTH", "EAST", "WEST")}


def one(args):
    f, team, out, check, canon_dir, nonoop = args
    dst = f"{out}/{os.path.basename(f).split('-replay')[0]}.npz"
    if os.path.exists(dst):
        return "skip"
    try:
        d = json.load(gzip.open(f, "rt") if f.endswith(".gz") else open(f))
        names = d["info"].get("TeamNames", [])
        if team not in names:
            return "noteam"
        p = names.index(team); T = len(d["steps"]) - 1
        canon = None
        if canon_dir:
            cf = os.path.join(canon_dir, os.path.basename(f).replace("-replay.json.gz", ".json"))
            cj = json.load(open(cf))
            if not cj.get("verified"):
                return f"ERR canon not verified {cf}"
            canon = cj["canon"][p]
        MS = np.zeros((T, F.MS_DIM), np.float32)
        B = np.zeros((T, F.C_BOARD, 10, 10), np.float16); G = np.zeros((T, F.G_DIM), np.float32)
        MT = np.zeros((T, F.N_SLOTS), np.int16); MQ = np.zeros((T, F.N_SLOTS), np.int16)
        ut, ui, ux, uy, uv, ua, uq = [], [], [], [], [], [], []
        snaps = []; bad = 0
        for t in range(T):
            o = F.merged_obs(d, t, p); a = d["steps"][t + 1][p]["action"] or {}
            snaps.append(F.snapshot(o, p)); snaps = snaps[-(F.LAGS + 1):]
            B[t] = F.board3(o, p); G[t] = F.glob3(o, p, F.hist_features(snaps))
            mk = canon[t] if canon is not None else a.get("market")
            if nonoop:  # NOOP slot alignment measured worthless for Boey (codec_ceiling canon_nonoop): drop from labels
                mk = [x for x in (mk or []) if x != ["NOOP"]]
            MT[t], MQ[t] = F.encode_market_seq(mk)
            if check and canon is None:
                sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); from codec_ceiling import market_seq
                if F.decode_market_seq([x for x in MT[t] if x != F.IGNORE], [max(q, 0) for q in MQ[t]]) != market_seq(a.get("market")):
                    bad += 1
            acts = [a.get("farmer")] + list(a.get("hands") or [])
            MS[t] = F.shed_after_units(o, p, acts)
            for i, (x, y, vec) in enumerate(F.units3(o, p)):
                c, q = F.encode_unit(acts[i] if i < len(acts) else None)
                ut.append(t); ui.append(i); ux.append(x); uy.append(y); uv.append(vec); ua.append(c); uq.append(q)
        ut_a = np.array(ut); ui_a = np.array(ui); ux_a = np.array(ux); uy_a = np.array(uy); ua_a = np.array(ua)
        key = {(int(t_), int(i_)): k for k, (t_, i_) in enumerate(zip(ut_a, ui_a))}
        tx = ux_a.copy(); ty = uy_a.copy()
        for k in range(len(ut_a)):  # target cell = where the unit does its next non-move action within the same day
            if ua_a[k] not in MOVES:
                continue
            t_, i_ = int(ut_a[k]), int(ui_a[k]); day = t_ // 24; j = k
            while True:
                nk = key.get((t_ + 1, i_))
                if nk is None or (t_ + 1) // 24 != day:
                    break
                t_ += 1; j = nk
                if ua_a[j] not in MOVES:
                    break
            tx[k], ty[k] = ux_a[j], uy_a[j]
        r = d["rewards"]
        np.savez_compressed(dst, B=B, G=G, MT=MT, MQ=MQ, MS=MS, ut=ut_a.astype(np.int32), ui=ui_a.astype(np.int8),
                            ux=ux_a.astype(np.int8), uy=uy_a.astype(np.int8), uv=np.array(uv, np.float32),
                            ua=ua_a.astype(np.int16), uq=np.array(uq, np.int16), tx=tx.astype(np.int8), ty=ty.astype(np.int8),
                            won=np.array(r[p] > r[1 - p]), margin=np.array(r[p] - r[1 - p]), seat=np.array(p))
        return f"ok bad={bad}" if check else "ok"
    except Exception as e:
        import traceback
        return f"ERR {f}: {e!r} {traceback.format_exc()[-600:]}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--team"); ap.add_argument("--glob"); ap.add_argument("--out")
    ap.add_argument("--workers", type=int, default=16); ap.add_argument("--check", action="store_true"); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--canon", default="", help="dir with canon_market.py outputs for these replays")
    ap.add_argument("--nonoop", action="store_true", help="drop NOOP slots from market labels")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    fs = sorted(glob.glob(a.glob))
    if a.limit:
        fs = fs[: a.limit]
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(one, [(f, a.team, a.out, a.check, a.canon, a.nonoop) for f in fs]))
    from collections import Counter
    print(Counter(r.split(" ")[0] for r in res)); print([r for r in res if not r.startswith(("ok", "skip"))][:3]); print(Counter(r for r in res if r.startswith("ok")))
