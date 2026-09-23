"""Throughput + where-the-time-goes attribution.

Reports, per batch size: end-to-end env-steps/s and episodes/s, GPU kernel time
vs CPU/launch time per step, and the per-phase split (unit lane / market lane /
town+decay / end-of-day).

    python -m gpuenv.tests.profile_step --batch 256,1024,4096
"""

from __future__ import annotations

import argparse
import time

import torch

from gpuenv import _mt19937 as MT
from gpuenv._consts import LAST_STEP, TURNS_PER_DAY
from gpuenv._daily import decay_plants, end_of_day, town_consume
from gpuenv._market import process_market
from gpuenv.env import VecKaggriculture
from gpuenv.tests.bench import replay_actions

N_STEPS = LAST_STEP + 1


def run_episode(env, st, seq, steps):
    for t in range(steps):
        st, _, _, _ = env.step(st, seq[t])
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=str, default="256,1024,4096")
    ap.add_argument("--steps", type=int, default=N_STEPS)
    ap.add_argument("--device", type=str, default="cuda")
    args = ap.parse_args()

    print(f"{'B':>7} {'ms/step':>9} {'env-steps/s':>13} {'eps/s':>8} "
          f"{'gpu ms':>8} {'cpu ms':>8} {'unit%':>7} {'mkt%':>6} {'town%':>7} {'eod%':>6}")
    for b in [int(x) for x in args.batch.split(",")]:
        env = VecKaggriculture(n_envs=b, device=args.device)
        st = env.reset(torch.arange(b, dtype=torch.int64))
        seq = replay_actions(b, env.max_hands, env.max_orders, args.device)

        # warm the graphs / allocator on a throwaway state
        run_episode(env, st, seq, 60)
        st = env.reset(torch.arange(b, dtype=torch.int64))
        torch.cuda.synchronize()

        t0 = time.time()
        st = run_episode(env, st, seq, args.steps)
        torch.cuda.synchronize()
        wall = time.time() - t0
        ms = wall / args.steps * 1e3
        eps = b * args.steps / wall

        # --- GPU kernel time vs CPU time (profiler, short window) -----------
        from torch.profiler import ProfilerActivity, profile
        st2 = env.reset(torch.arange(b, dtype=torch.int64))
        run_episode(env, st2, seq, 30)
        torch.cuda.synchronize()
        with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA]) as prof:
            run_episode(env, st2, seq, 60)
            torch.cuda.synchronize()
        ka = prof.key_averages()
        gpu_us = sum(e.self_device_time_total for e in ka)
        cpu_us = sum(e.self_cpu_time_total for e in ka)
        gpu_ms = gpu_us / 60 / 1e3
        cpu_ms = cpu_us / 60 / 1e3

        # --- per-phase split (explicit syncs; adds a little overhead) -------
        st3 = env.reset(torch.arange(b, dtype=torch.int64))
        tot = {"unit": 0.0, "mkt": 0.0, "town": 0.0, "eod": 0.0}
        n = 240

        def timed(key, fn):
            torch.cuda.synchronize()
            t = time.time()
            fn()
            torch.cuda.synchronize()
            tot[key] += time.time() - t

        for t in range(n):
            a = seq[t]
            ua = a.unit_actions()
            env._day_t.fill_(t // TURNS_PER_DAY)
            env._step_t.fill_(t)

            def unit():
                env._ua_buf.copy_(ua)
                k = env._ladder(int(st3.n_hands.max()) + 1)
                g = env._graphs.get(k) or env._capture(st3, k)
                g.replay()
            timed("unit", unit)
            timed("mkt", lambda: process_market(st3, a.market.to(torch.int64),
                                                env.max_hands))
            timed("town", lambda: (town_consume(st3, t), decay_plants(st3, t)))
            if (t + 1) % TURNS_PER_DAY == 0:
                w = (MT.gen_words((st3.seed * 1_000_003) ^ (t // TURNS_PER_DAY))
                     if env.rng_lazy else None)
                timed("eod", lambda: end_of_day(st3, t // TURNS_PER_DAY,
                                                env.max_hands, w))
            st3.step = st3.step + 1
        s = sum(tot.values())
        print(f"{b:7d} {ms:9.2f} {eps / 1e3:11.1f}k {eps / N_STEPS:8.1f} "
              f"{gpu_ms:8.2f} {cpu_ms:8.2f} "
              f"{tot['unit'] / s * 100:6.1f}% {tot['mkt'] / s * 100:5.1f}% "
              f"{tot['town'] / s * 100:6.1f}% {tot['eod'] / s * 100:5.1f}%")


if __name__ == "__main__":
    main()
