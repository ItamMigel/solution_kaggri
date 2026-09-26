"""CFM over per-turn sell fractions (9 items) | 43 conditioning features. Evaluates sell/hold agreement per steep item vs an hour/day baseline."""
import sys, json, numpy as np, torch, torch.nn as nn
d = np.load(sys.argv[1]); x, c = d["x"], d["c"]; items = list(d["items"]); out = sys.argv[2]
rng = np.random.default_rng(0); idx = rng.permutation(len(x)); te = idx[:40000]; tr = idx[40000:]
mu_c, sd_c = c[tr].mean(0), c[tr].std(0) + 1e-3; cn = ((c - mu_c) / sd_c).astype(np.float32); xs = (x * 2 - 1).astype(np.float32)   # [0,1] -> [-1,1]
D, Cd = x.shape[1], c.shape[1]; dev = "cuda" if torch.cuda.is_available() else "cpu"
net = nn.Sequential(nn.Linear(D + 1 + Cd, 256), nn.SiLU(), nn.Linear(256, 256), nn.SiLU(), nn.Linear(256, 256), nn.SiLU(), nn.Linear(256, D)).to(dev)
opt = torch.optim.Adam(net.parameters(), 1e-3); Z = torch.tensor(xs, device=dev); CC = torch.tensor(cn, device=dev); trt = torch.tensor(tr, device=dev)
for it in range(int(sys.argv[3]) if len(sys.argv) > 3 else 8000):
    b = trt[torch.randint(len(trt), (4096,), device=dev)]; z1 = Z[b]; z0 = torch.randn_like(z1); t = torch.rand(len(b), 1, device=dev)
    loss = ((net(torch.cat([(1 - t) * z0 + t * z1, t, CC[b]], 1)) - (z1 - z0)) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step()
    if it % 2000 == 0: print(it, loss.item(), flush=True)
with torch.no_grad():
    cb = CC[torch.tensor(te, device=dev)]; zs = []
    for _ in range(4):
        z = torch.randn(len(cb), D, device=dev)
        for k in range(10): z = z + net(torch.cat([z, torch.full((len(cb), 1), k / 10, device=dev), cb], 1)) / 10
        zs.append(z)
    p = ((torch.stack(zs).mean(0) + 1) / 2).clamp(0, 1).cpu().numpy()
truth = x[te]; hour = np.round(c[te, 0] * 23).astype(int)
for i, it in enumerate(items):
    has = c[te, 2 + i] > 0          # log1p(stock) > 0 -> stock present
    if has.sum() < 200: continue
    y = truth[has, i] > 0.05
    best = max(((p[has, i] > th) == y).mean() for th in (0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6)); yh = p[has, i] > 0.25
    # baseline: sell if this hour's historical sell-rate (train) > 0.5 for this item
    hr_tr = np.round(c[tr, 0] * 23).astype(int); has_tr = c[tr, 2 + i] > 0
    rate = np.array([ (x[tr][has_tr & (hr_tr == h), i] > 0.05).mean() if (has_tr & (hr_tr == h)).any() else 0 for h in range(24)])
    yb = rate[hour[has]] > 0.5
    print(f"{it:10s} sell-rate {y.mean():.2f}  FM acc {(yh == y).mean():.3f} best-th {best:.3f}  hour-baseline acc {(yb == y).mean():.3f}  always-hold {(~y).mean():.3f}")
W = [(l.weight.detach().cpu().numpy().tolist(), l.bias.detach().cpu().numpy().tolist()) for l in net if isinstance(l, nn.Linear)]
json.dump({"W": W, "mu_c": mu_c.tolist(), "sd_c": sd_c.tolist(), "items": items}, open(out, "w"))
