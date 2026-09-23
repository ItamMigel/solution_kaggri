"""Throughput benchmark.  env-steps/s = B * steps / wall.

    python -m gpuenv.tests.bench --batch 1024,4096 --mode random
"""

from __future__ import annotations

import argparse
import time

import torch

from gpuenv import ops as O
from gpuenv._consts import LAST_STEP
from gpuenv._state import Actions
from gpuenv.env import VecKaggriculture


_REPLAY = {}


def replay_actions(b, max_hands, max_orders, device, agent="cand_b1", seed=1000):
    """Actions recorded from a real self-play episode, tiled across the batch.

    The most honest throughput input: real op mix, real market-order shapes.
    """
    key = (agent, seed, max_hands, max_orders)
    if key not in _REPLAY:
        from gpuenv._encode import encode_actions
        from gpuenv.tests.local_difftest import load_agent, run_reference
        acts, _, _ = run_reference(seed, [load_agent(agent, 0), load_agent(agent, 1)],
                                   LAST_STEP + 1, max_hands + 1)
        enc = [encode_actions([p], max_hands, max_orders, device="cpu") for p in acts]
        _REPLAY[key] = enc
    enc = _REPLAY[key]
    # keep one [1, ...] copy per step on device and expand (no per-batch copy)
    out = []
    for a in enc:
        f = a.farmer.to(device)
        h = a.hands.to(device)
        m = a.market.to(device)
        out.append(Actions(f.expand(b, -1, -1), h.expand(b, -1, -1, -1),
                           m.expand(b, -1, -1, -1)))
    return out


def make_actions(b, max_hands, max_orders, device, mode, g):
    if mode == "idle":
        f = torch.zeros((b, 2, 3), dtype=torch.int32, device=device)
        h = torch.zeros((b, 2, max_hands, 3), dtype=torch.int32, device=device)
        m = torch.zeros((b, 2, max_orders, 3), dtype=torch.int32, device=device)
        return Actions(f, h, m)

    def units(shape):
        op = torch.randint(0, O.N_UNIT_OPS, shape, device=device, generator=g, dtype=torch.int32)
        a1 = torch.randint(0, O.N_ITEMS, shape, device=device, generator=g, dtype=torch.int32)
        a2 = torch.randint(1, 12, shape, device=device, generator=g, dtype=torch.int32)
        return torch.stack([op, a1, a2], dim=-1)

    f = units((b, 2))
    h = units((b, 2, max_hands))
    # market: mostly empty, a few live orders per turn
    op = torch.randint(0, O.N_MARKET_OPS, (b, 2, max_orders), device=device,
                       generator=g, dtype=torch.int32)
    live = torch.rand((b, 2, max_orders), device=device, generator=g) < 0.25
    op = torch.where(live, op, torch.zeros_like(op))
    item = torch.randint(0, O.N_ITEMS, (b, 2, max_orders), device=device,
                         generator=g, dtype=torch.int32)
    qty = torch.randint(1, 40, (b, 2, max_orders), device=device, generator=g, dtype=torch.int32)
    m = torch.stack([op, item, qty], dim=-1)
    return Actions(f, h, m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=str, default="256,1024,4096")
    ap.add_argument("--mode", type=str, default="random")
    ap.add_argument("--steps", type=int, default=LAST_STEP + 1)
    ap.add_argument("--device", type=str, default="cuda")
    ap.add_argument("--regen", type=int, default=1,
                    help="regenerate random actions every step (realistic) or reuse")
    args = ap.parse_args()

    for b in [int(x) for x in args.batch.split(",")]:
        g = torch.Generator(device=args.device).manual_seed(0)
        env = VecKaggriculture(n_envs=b, device=args.device)
        st = env.reset(torch.arange(b, dtype=torch.int64))
        if args.mode == "replay":
            seq = replay_actions(b, env.max_hands, env.max_orders, args.device)
            acts = seq[0]
        else:
            acts = make_actions(b, env.max_hands, env.max_orders, args.device, args.mode, g)
        torch.cuda.synchronize()
        t0 = time.time()
        for t in range(args.steps):
            if args.mode == "replay":
                acts = seq[t]
            elif args.regen and args.mode != "idle":
                acts = make_actions(b, env.max_hands, env.max_orders, args.device, args.mode, g)
            st, r, d, info = env.step(st, acts)
        torch.cuda.synchronize()
        dt = time.time() - t0
        print(f"B={b:6d}  {args.steps} steps  {dt:7.2f}s  "
              f"{b * args.steps / dt / 1e3:9.1f}k env-steps/s   "
              f"({dt / args.steps * 1e3:.2f} ms/step)")


if __name__ == "__main__":
    main()
