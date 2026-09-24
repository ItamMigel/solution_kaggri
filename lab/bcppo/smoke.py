import sys, os, time, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import policy, gpufeat
from gpuenv.env import VecKaggriculture
B = int(sys.argv[1]) if len(sys.argv) > 1 else 64
dev = "cuda"
ck = torch.load("/workspace/shared/bc_runs/v2/final.pt", map_location=dev)
net = policy.PolicyNet(ck["gdim"]).to(dev); missing = net.load_state_dict(ck["state"], strict=False); print("missing", missing.missing_keys)
net.eval(); team = torch.tensor([[0., 1., 0.]], device=dev)
ve = VecKaggriculture(B, device=dev); st = ve.reset(torch.arange(1, B + 1, device=dev) * 7919)
so = gpufeat.ShopOrder(B, dev); t0 = time.time()
with torch.no_grad():
    for t in range(719):
        so.update(st)
        a0, lp0, v0, e0, r0 = policy.act(net, st, 0, so, team, greedy=True)
        a1, lp1, v1, e1, r1 = policy.act(net, st, 1, so, team, greedy=False)
        st, rew, done, info = ve.step(st, policy.combine(a0, a1))
        if t in (0, 100, 300, 718): print(t, "money p0 mean %.0f p1 %.0f" % (st.money[:, 0].float().mean(), st.money[:, 1].float().mean()), "%.1fs" % (time.time() - t0), flush=True)
print("final p0 (greedy) mean %.0f max %.0f | p1 (sampled) mean %.0f max %.0f" % (st.money[:, 0].float().mean(), st.money[:, 0].max(), st.money[:, 1].float().mean(), st.money[:, 1].max()))
print("steps/s", B * 719 / (time.time() - t0))
