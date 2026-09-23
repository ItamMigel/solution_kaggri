"""Large differential-test suite: many agent pairs x many seeds.

Reference episodes are generated in parallel across CPU cores, then replayed
through the batched env in chunks and compared field-by-field on the GPU at
every step.

    python -m gpuenv.tests.validate_suite --episodes 96 --chunk 16 --workers 24
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import sys
import time

import numpy as np
import torch

from gpuenv._consts import LAST_STEP
from gpuenv._encode import encode_actions, ref_snapshot
from gpuenv.env import VecKaggriculture
from gpuenv.tests.local_difftest import load_agent, run_reference

FIELDS = ["money", "tiles", "shed", "seeds", "inv", "ux", "uy", "n_hands",
          "hires_today", "land", "market_inv", "shops"]

DEFAULT_PAIRS = [
    ("starter", "starter"),
    ("random", "starter"),
    ("cand_b1", "cand_b1"),
    ("cand_b1", "best_exp019"),
    ("cand_animal", "best_exp022"),
    ("best_exp023", "cand_b1"),
    ("chaos:cand_b1", "chaos:cand_b1"),
    ("chaos:cand_b1", "chaos:best_exp019"),
    ("chaos:cand_animal", "starter"),
    ("fuzz", "fuzz"),
    ("fuzz", "cand_b1"),
    ("chaos:best_exp022", "fuzz"),
]


def _job(arg):
    seed, names, salt, max_units, steps = arg
    agents = [load_agent(names[p], salt=salt * 7 + p) for p in range(2)]
    acts, snaps, rseed = run_reference(seed, agents, steps, max_units)
    packed = {f: np.stack([s[f] for s in snaps]) for f in FIELDS}
    return acts, packed, rseed, names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=96)
    ap.add_argument("--chunk", type=int, default=16)
    ap.add_argument("--workers", type=int, default=min(24, os.cpu_count() or 8))
    ap.add_argument("--seed0", type=int, default=5000)
    ap.add_argument("--steps", type=int, default=LAST_STEP + 1)
    ap.add_argument("--max-hands", type=int, default=24)
    ap.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    jobs = []
    for i in range(args.episodes):
        names = DEFAULT_PAIRS[i % len(DEFAULT_PAIRS)]
        jobs.append((args.seed0 + i, names, i, args.max_hands + 1, args.steps))

    n_fail = 0
    t_start = time.time()
    for c0 in range(0, len(jobs), args.chunk):
        chunk = jobs[c0:c0 + args.chunk]
        t0 = time.time()
        with mp.Pool(min(args.workers, len(chunk))) as pool:
            results = pool.map(_job, chunk)
        t_ref = time.time() - t0

        b = len(results)
        n_steps = min(r[1]["money"].shape[0] for r in results)
        seeds = [r[2] for r in results]
        ref = {f: torch.from_numpy(
            np.stack([r[1][f][:n_steps] for r in results], axis=1)).to(args.device)
            for f in FIELDS}

        env = VecKaggriculture(n_envs=b, device=args.device, max_hands=args.max_hands)
        st = env.reset(torch.tensor(seeds, dtype=torch.int64))
        bad = []
        t1 = time.time()
        for t in range(n_steps):
            pairs = [results[i][0][t] for i in range(b)]
            acts = encode_actions(pairs, env.max_hands, env.max_orders, device=args.device)
            st, _, _, _ = env.step(st, acts)
            got = _pack(st, env)
            for f in FIELDS:
                if not torch.equal(got[f], ref[f][t]):
                    diff = (got[f] != ref[f][t])
                    while diff.dim() > 1:
                        diff = diff.any(-1)
                    envs = torch.nonzero(diff).flatten().tolist()
                    bad.append((t, f, envs[:4]))
                    break
            if bad:
                break
        t_gpu = time.time() - t1
        tag = f"[{c0}:{c0 + b}]"
        if bad:
            n_fail += 1
            t, f, envs = bad[0]
            print(f"{tag} FAIL step={t} field={f} envs={envs} "
                  f"(seeds {[seeds[e] for e in envs]}, "
                  f"agents {[results[e][3] for e in envs]})")
        else:
            print(f"{tag} OK  {b} eps x {n_steps} steps  "
                  f"(ref {t_ref:.0f}s, gpu+cmp {t_gpu:.0f}s)")
        sys.stdout.flush()
    print(f"DONE: {args.episodes} episodes, {n_fail} failing chunks, "
          f"{time.time() - t_start:.0f}s")
    return 1 if n_fail else 0


def _pack(st, env):
    from gpuenv._encode import _TILE_FIELDS
    tiles = torch.stack([getattr(st, f).to(torch.int64) for f in _TILE_FIELDS], dim=-1)
    n_hands = st.n_hands.to(torch.int64)
    u = torch.arange(st.ux.shape[2], device=st.ux.device).view(1, 1, -1)
    live = u <= n_hands.unsqueeze(-1)
    ux = torch.where(live, st.ux.to(torch.int64), torch.full_like(n_hands.unsqueeze(-1), 4))
    uy = torch.where(live, st.uy.to(torch.int64), torch.full_like(n_hands.unsqueeze(-1), 4))
    inv = st.inv * live.unsqueeze(-1)
    return {
        "money": st.money, "tiles": tiles, "shed": st.shed, "seeds": st.seeds,
        "inv": inv, "ux": ux, "uy": uy, "n_hands": n_hands,
        "hires_today": st.hires_today.to(torch.int64),
        "land": st.land.to(torch.int64),
        "market_inv": st.market_inv, "shops": st.shops.to(torch.int64),
    }


if __name__ == "__main__":
    sys.exit(main())
