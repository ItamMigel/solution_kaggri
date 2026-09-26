"""Conditional flow matching over next-day macro deltas: z0~N(0,I) -> z1 = (y-x)/s; v_theta(z_t, t, [x_norm, c]) regresses z1 - z0."""
import sys, json, numpy as np, torch, torch.nn as nn
d = np.load(sys.argv[1]); x, y, c = d["x"], d["y"], d["c"]; out = sys.argv[2]
rng = np.random.default_rng(0); idx = rng.permutation(len(x)); te = idx[: len(x) // 10]; tr = idx[len(x) // 10:]
delta = y - x; mu_x, sd_x = x[tr].mean(0), x[tr].std(0) + 1e-3; mu_d, sd_d = delta[tr].mean(0), delta[tr].std(0) + 1e-3
xn = (x - mu_x) / sd_x; dn = (delta - mu_d) / sd_d; cond = np.concatenate([xn, c], 1).astype(np.float32)
D, Cd = dn.shape[1], cond.shape[1]; dev = "cuda" if torch.cuda.is_available() else "cpu"
net = nn.Sequential(nn.Linear(D + 1 + Cd, 256), nn.SiLU(), nn.Linear(256, 256), nn.SiLU(), nn.Linear(256, 256), nn.SiLU(), nn.Linear(256, D)).to(dev)
opt = torch.optim.Adam(net.parameters(), 1e-3); Z = torch.tensor(dn, device=dev); CC = torch.tensor(cond, device=dev); trt = torch.tensor(tr, device=dev)
for it in range(6000):
    b = trt[torch.randint(len(trt), (1024,), device=dev)]; z1 = Z[b]; z0 = torch.randn_like(z1); t = torch.rand(len(b), 1, device=dev)
    zt = (1 - t) * z0 + t * z1; pred = net(torch.cat([zt, t, CC[b]], 1)); loss = ((pred - (z1 - z0)) ** 2).mean()
    opt.zero_grad(); loss.backward(); opt.step()
    if it % 1000 == 0: print(it, float(loss), flush=True)
def sample(cb, steps=20, n=1):
    z = torch.randn(len(cb), D, device=dev)
    for k in range(steps):
        t = torch.full((len(cb), 1), k / steps, device=dev); z = z + net(torch.cat([z, t, cb], 1)) / steps
    return z
with torch.no_grad():
    cb = CC[torch.tensor(te, device=dev)]; zs = torch.stack([sample(cb) for _ in range(8)]).mean(0).cpu().numpy()
pred = zs * sd_d + mu_d; true = delta[te]
base_day = np.zeros_like(true)
for i, j in enumerate(te):   # baseline: mean delta for the same day index
    dd = c[j, 0]; m = np.abs(c[tr, 0] - dd) < 1e-6; base_day[i] = delta[tr][m].mean(0)
names = list(d["names"])
mae = np.abs(pred - true).mean(0); mae_b = np.abs(base_day - true).mean(0); mae_0 = np.abs(true).mean(0)
for n_, a, b_, z_ in zip(names, mae, mae_b, mae_0): print(f"{n_:12s} FM {a:6.3f}  day-mean {b_:6.3f}  no-change {z_:6.3f}")
print("TOTAL FM %.3f day-mean %.3f no-change %.3f" % (mae.mean(), mae_b.mean(), mae_0.mean()))
W = [(l.weight.detach().cpu().numpy().tolist(), l.bias.detach().cpu().numpy().tolist()) for l in net if isinstance(l, nn.Linear)]
json.dump({"W": W, "mu_x": mu_x.tolist(), "sd_x": sd_x.tolist(), "mu_d": mu_d.tolist(), "sd_d": sd_d.tolist(), "names": names}, open(out, "w"))
