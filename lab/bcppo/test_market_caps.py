"""P0/P1 regression: sampled market buckets are exactly what the engine receives (random logits, adversarial high buckets)."""
import os, sys, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import policy, feat
from gpuenv import ops as O
torch.manual_seed(0)
B = 4096; dev = "cuda" if torch.cuda.is_available() else "cpu"
ml = torch.randn(B, policy.NK, policy.NB, device=dev) * 3
ml[:, :, 20:] += 4.0                                    # push mass to large buckets to stress the 10-slot cap
hire_max = torch.randint(0, 17, (B,), device=dev); land_max = torch.randint(0, 4, (B,), device=dev)
mb, mcap = policy.sample_market(ml, hire_max, land_max, greedy=False)
orders = policy.build_market(mb)
assert (mb <= mcap).all(), "bucket above cap"
n_orders = (orders[..., 0] != O.MKT_NONE).sum(1)
rep = policy.MKT_REP.to(dev)
expected = (mb * rep).sum(1) + ((mb > 0) & ~rep).sum(1)
assert (n_orders == expected).all(), "emitted order count != recorded buckets"
assert (n_orders <= O.MAX_ORDERS).all()
h = feat.MKT_IDX["HIRE"]; l = feat.MKT_IDX["BUY_LAND"]
assert (mb[:, h] <= hire_max).all() and (mb[:, l] <= land_max).all()
rec = dict(umask=torch.zeros(B, 1, dtype=torch.bool, device=dev), t=torch.zeros(B, 1, dtype=torch.int8, device=dev), o=torch.zeros(B, 1, dtype=torch.int8, device=dev),
           opm=torch.ones(B, 1, policy.NOP, dtype=torch.bool, device=dev), mb=mb.to(torch.int8), mcap=mcap.to(torch.int8))
lp, ent = policy.logprob(torch.zeros(B, 1, policy.NOP, device=dev), torch.zeros(B, 1, 100, device=dev), ml, rec)
assert torch.isfinite(lp).all() and (lp <= 0).all()
zero_cap = mcap == 0
mlp = torch.log_softmax(policy.market_mask(ml, mcap), -1)
ent_k = -(mlp.exp() * mlp.clamp(min=-30)).sum(-1)
assert (ent_k[zero_cap].abs() < 1e-6).all(), "entropy of fully-capped heads must be 0"
print("OK market caps:", int(n_orders.float().mean().item() * 100) / 100, "orders avg; saturated rows", int((n_orders == 10).sum()))
