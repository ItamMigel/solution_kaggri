"""The market fast path must be bit-identical to the literal lockstep loop.

Randomised states x randomised order slots, including the cases that matter:
both players selling the same item (self-play mirror), one player draining the
curve past the $1 floor, BUY_PRODUCT walking the curve upward, and mixed
SELL/BUY_PRODUCT on the same item (which the fast path routes back to the loop).

    python -m gpuenv.tests.test_market_equiv
"""

from __future__ import annotations

import sys

import torch

from gpuenv import ops as O
from gpuenv._market import process_market
from gpuenv.env import VecKaggriculture

FIELDS = ("money", "shed", "seeds", "market_inv", "n_hands", "hires_today",
          "land", "kind", "ux", "uy")


def random_orders(b, n_slots, g, device, mirror_p=0.35):
    op = torch.randint(0, O.N_MARKET_OPS, (b, 2, n_slots), generator=g, device=device)
    item = torch.randint(0, O.N_ITEMS, (b, 2, n_slots), generator=g, device=device)
    qty = torch.randint(1, 160, (b, 2, n_slots), generator=g, device=device)
    live = torch.rand((b, 2, n_slots), generator=g, device=device) < 0.5
    op = torch.where(live, op, torch.zeros_like(op))
    # force a decent fraction of exact mirrors (both players, same op+item)
    mir = torch.rand((b, 1, n_slots), generator=g, device=device) < mirror_p
    op = torch.where(mir, op[:, :1], op)
    item = torch.where(mir, item[:, :1], item)
    return torch.stack([op, item, qty], dim=-1).to(torch.int64)


def randomise_state(st, g):
    b = st.money.shape[0]
    dev = st.money.device
    st.money.copy_(torch.randint(0, 60000, st.money.shape, generator=g, device=dev))
    st.shed.copy_(torch.randint(0, 40, st.shed.shape, generator=g, device=dev))
    st.market_inv.copy_(9700 + torch.randint(0, 700, st.market_inv.shape,
                                             generator=g, device=dev))
    st.n_hands.copy_(torch.randint(0, 6, st.n_hands.shape, generator=g,
                                   device=dev).to(st.n_hands.dtype))
    st.hires_today.copy_(torch.randint(0, 10, st.hires_today.shape, generator=g,
                                       device=dev).to(st.hires_today.dtype))
    st.land.copy_(torch.randint(0, 4, st.land.shape, generator=g,
                                device=dev).to(st.land.dtype))


def main(trials=60, b=512, device="cuda" if torch.cuda.is_available() else "cpu"):
    g = torch.Generator(device=device).manual_seed(7)
    env = VecKaggriculture(b, device, cuda_graph=False)
    bad = 0
    for trial in range(trials):
        st_a = env.reset(torch.arange(b), rng=False)
        randomise_state(st_a, g)
        st_b = st_a.clone()
        orders = random_orders(b, env.max_orders, g, device)
        process_market(st_a, orders, env.max_hands, exact_loop=True)
        process_market(st_b, orders, env.max_hands, exact_loop=False)
        for f in FIELDS:
            x, y = getattr(st_a, f), getattr(st_b, f)
            if not torch.equal(x, y):
                idx = torch.nonzero((x != y).reshape(b, -1).any(-1)).flatten()[:3]
                print(f"trial {trial}: field {f} differs in envs {idx.tolist()}")
                for e in idx.tolist():
                    print("   loop:", x[e].flatten()[:12].tolist())
                    print("   fast:", y[e].flatten()[:12].tolist())
                    print("   orders:", orders[e].tolist())
                bad += 1
                break
        if bad >= 3:
            break
    if bad:
        print(f"FAIL ({bad} mismatching trials)")
        return 1
    print(f"OK: {trials} trials x {b} envs, fast path == exact loop.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
