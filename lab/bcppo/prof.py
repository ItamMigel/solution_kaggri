import sys, os, time, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import policy, gpufeat
from gpuenv.env import VecKaggriculture
B = int(sys.argv[1]); dev = "cuda"
ck = torch.load("/workspace/shared/bc_runs/v2/final.pt", map_location=dev)
net = policy.PolicyNet(ck["gdim"]).to(dev); net.load_state_dict(ck["state"], strict=False); net.eval(); team = torch.tensor([[0., 1., 0.]], device=dev)
ve = VecKaggriculture(B, device=dev); st = ve.reset(torch.arange(1, B + 1, device=dev) * 7919); so = gpufeat.ShopOrder(B, dev)
def tm(f):
    torch.cuda.synchronize(); t = time.time(); r = f(); torch.cuda.synchronize(); return r, time.time() - t
with torch.no_grad():
    for t in range(150):
        so.update(st); a0, lp0, v0, e0, r0 = policy.act(net, st, 0, so, team); a1, *_ = policy.act(net, st, 1, so, team)
        st, *_ = ve.step(st, policy.combine(a0, a1))
    T = {}
    for k in range(20):
        (feats, T_f) = tm(lambda: gpufeat.features(st, 0, so)); T['features'] = T.get('features', 0) + T_f
        board, G, uv, ux, uy, um = feats; G2 = torch.cat([G, team.expand(B, -1)], 1)
        (_, T_m) = tm(lambda: policy.legal_masks(st, 0, ux, uy, um)); T['masks'] = T.get('masks', 0) + T_m
        (out, T_n) = tm(lambda: net.full(board, G2, uv, ux, uy, um)); T['net'] = T.get('net', 0) + T_n
        (_, T_a) = tm(lambda: policy.act(net, st, 0, so, team)); T['act_total'] = T.get('act_total', 0) + T_a
        acts = policy.combine(a0, a1)
        (_, T_s) = tm(lambda: ve.step(st, acts)); T['env_step'] = T.get('env_step', 0) + T_s
    print({k: round(v / 20 * 1000, 1) for k, v in T.items()}, 'ms')
