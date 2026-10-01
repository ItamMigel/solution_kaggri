"""T045 B1: fix day-boundary MOVE target labels in existing BC3 NPZ files (copy to a new dir; originals untouched).

build3.py sets a MOVE's target to the cell of the next non-move action *within the same day*. When the chain of MOVEs
reaches the day boundary (hour 23) without a non-move, the target became the cell *before* the last move, often the unit's
current cell - which agent3 turns into "do not move" (target==current masks all MOVEs). Fix: for such chains the target is
the cell reached *after* the last move (unit position at the next step if it exists, else current cell + move delta).
usage: python fix_targets.py --src bc3_data/mgoose_cn --dst bc3_data_b1/mgoose_cn [--workers 16]
Prints how many unit labels changed. Run it on every team dir used by a recipe."""
import argparse, glob, os, sys
import numpy as np
from concurrent.futures import ProcessPoolExecutor

HERE = os.environ.get("BC3_DIR", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import feat3 as F  # noqa: E402

DELTA = {F.UNIT_IDX["NORTH"]: (0, -1), F.UNIT_IDX["SOUTH"]: (0, 1), F.UNIT_IDX["EAST"]: (1, 0), F.UNIT_IDX["WEST"]: (-1, 0)}


def fix(args):
    src, dst = args
    d = dict(np.load(src))
    ut, ui, ux, uy, ua = d["ut"], d["ui"], d["ux"], d["uy"], d["ua"]
    tx, ty = d["tx"].copy(), d["ty"].copy()
    key = {(int(t), int(i)): k for k, (t, i) in enumerate(zip(ut, ui))}
    changed = 0
    for k in range(len(ut)):
        if int(ua[k]) not in DELTA:
            continue
        t_, i_ = int(ut[k]), int(ui[k]); day = t_ // 24; j = k; ended_on_move = True
        while True:
            nk = key.get((t_ + 1, i_))
            if nk is None or (t_ + 1) // 24 != day:
                break
            t_ += 1; j = nk
            if int(ua[j]) not in DELTA:
                ended_on_move = False
                break
        if not ended_on_move:
            continue  # unchanged: original rule already points at the next non-move cell
        # chain ended on a MOVE: either the day ended (h23 -> next obs is the night reset, NOT the move result) or the unit
        # vanished. Target = cell after the last move, from its direction (clamped to the board). (Codex T046 fixture fix.)
        dx, dy = DELTA[int(ua[j])]; nx, ny = int(ux[j]) + dx, int(uy[j]) + dy
        nx = min(max(nx, 0), F.N - 1); ny = min(max(ny, 0), F.N - 1)
        if (nx, ny) != (int(tx[k]), int(ty[k])):
            tx[k], ty[k] = nx, ny; changed += 1
    d["tx"], d["ty"] = tx.astype(np.int8), ty.astype(np.int8)
    np.savez_compressed(dst, **d)
    return changed, int(sum(int(a) in DELTA for a in ua))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--src", required=True); ap.add_argument("--dst", required=True)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args(); os.makedirs(a.dst, exist_ok=True)
    fs = sorted(glob.glob(f"{a.src}/*.npz"))
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(fix, [(f, os.path.join(a.dst, os.path.basename(f))) for f in fs]))
    ch = sum(r[0] for r in res); mv = sum(r[1] for r in res)
    print(f"{a.src}: {len(fs)} files, move labels {mv}, changed targets {ch} ({100 * ch / max(1, mv):.2f}%)")
