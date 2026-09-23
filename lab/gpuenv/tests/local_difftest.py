"""Local differential test: real interpreter vs. VecKaggriculture.

Runs N reference episodes (recording every action dict and a full canonical
post-step snapshot), then replays all N action sequences through the batched env
in a single batch and compares the full state at every step.

    python -m gpuenv.tests.local_difftest --episodes 4 --agents starter,random

(run from ``src/`` or with ``src`` on PYTHONPATH)
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import random
import sys
import time

import numpy as np
import torch

from gpuenv._encode import diff_snapshots, encode_actions, gpu_snapshot, ref_snapshot
from gpuenv.env import VecKaggriculture
from gpuenv._consts import LAST_STEP

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))


def load_agent(name: str, salt: int = 0):
    import kaggle_environments.envs.kaggriculture.kaggriculture as K
    if name.startswith("fuzz"):
        from gpuenv.tests.fuzz_agent import make_fuzz_agent
        return make_fuzz_agent(hash((name, salt)) & 0xFFFFFF)
    if name.startswith("chaos:"):
        from gpuenv.tests.fuzz_agent import make_chaos_agent
        return make_chaos_agent(load_agent(name.split(":", 1)[1], salt),
                                hash((name, salt)) & 0xFFFFFF)
    if name in K.agents:
        return K.agents[name]
    path = name if os.path.exists(name) else os.path.join(ROOT, "artifacts", "agents", name)
    if not path.endswith(".py"):
        path += ".py"
    spec = importlib.util.spec_from_file_location("agent_" + os.path.basename(path), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fns = [v for k, v in vars(mod).items() if callable(v) and getattr(v, "__module__", None) == mod.__name__]
    return fns[-1]


def run_reference(seed: int, agents, max_steps: int, max_units: int = 17):
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    state = env.reset(2)
    actions, snaps = [], []
    for t in range(max_steps):
        pair = []
        for p in range(2):
            try:
                a = agents[p](state[p].observation)
            except Exception:
                a = {"farmer": ["PASS"], "hands": [], "market": []}
            pair.append(a)
        actions.append(pair)
        state = env.step(pair)
        snaps.append(ref_snapshot(state, max_units))
        if env.done:
            break
    return actions, snaps, int(env.info["seed"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=2)
    ap.add_argument("--agents", type=str, default="starter,starter")
    ap.add_argument("--seed0", type=int, default=1000)
    ap.add_argument("--steps", type=int, default=LAST_STEP + 1)
    ap.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--max-report", type=int, default=6)
    ap.add_argument("--max-hands", type=int, default=16)
    args = ap.parse_args()

    names = args.agents.split(",")
    if len(names) == 1:
        names = names * 2
    n = args.episodes

    all_actions, all_snaps, seeds = [], [], []
    t0 = time.time()
    for i in range(n):
        seed = args.seed0 + i
        random.seed(12345 + i)
        pair = [load_agent(names[p % len(names)], salt=i * 7 + p) for p in range(2)]
        acts, snaps, rseed = run_reference(seed, pair, args.steps, args.max_hands + 1)
        all_actions.append(acts)
        all_snaps.append(snaps)
        seeds.append(rseed)
        mh = max(int(s['n_hands'].max()) for s in snaps)
        print(f"  ref episode {i} seed={rseed} steps={len(snaps)} maxhands={mh} "
              f"money={snaps[-1]['money'].tolist()}  ({time.time() - t0:.1f}s)")
    n_steps = min(len(s) for s in all_snaps)

    env = VecKaggriculture(n_envs=n, device=args.device, max_hands=args.max_hands)
    st = env.reset(torch.tensor(seeds, dtype=torch.int64))

    n_bad = 0
    for t in range(n_steps):
        pairs = [all_actions[i][t] for i in range(n)]
        acts = encode_actions(pairs, env.max_hands, env.max_orders, device=args.device)
        st, reward, done, info = env.step(st, acts)
        for i in range(n):
            got = gpu_snapshot(st, i)
            d = diff_snapshots(all_snaps[i][t], got)
            if d:
                n_bad += 1
                print(f"DIVERGENCE env={i} seed={seeds[i]} step={t} day={t // 24} "
                      f"hour={t % 24}")
                for k, msg in d:
                    print(f"    {k}: {msg}")
                if n_bad >= args.max_report:
                    print("...stopping after %d divergences" % n_bad)
                    return 1
    print(f"OK: {n} episodes x {n_steps} steps, full state identical.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
