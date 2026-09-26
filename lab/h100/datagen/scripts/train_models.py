"""GPU training: (1) conditional flow-matching world model over next-day macro deltas | (state, day, shops, opp, agent);
(2) value model E[final margin], E[final money] | (state, day, shops, opp, agent). Exports JSON weights for the stdlib/numpy agents."""
import sys, json, numpy as np, torch, torch.nn as nn
d = np.load(sys.argv[1]); out = sys.argv[2]; dev = "cuda" if torch.cuda.is_available() else "cpu"; H = int(sys.argv[3]) if len(sys.argv) > 3 else 512
agents = list(d["agents"]); rng = np.random.default_rng(0)
def mlp(i, o, h=H, L=4):
    layers = [nn.Linear(i, h), nn.SiLU()]
    for _ in range(L - 1): layers += [nn.Linear(h, h), nn.SiLU()]
    return nn.Sequential(*layers, nn.Linear(h, o)).to(dev)
def export(net): return [(l.weight.detach().cpu().numpy().tolist(), l.bias.detach().cpu().numpy().tolist()) for l in net if isinstance(l, nn.Linear)]
# ---- world model
x, y, c, a = d["x"], d["y"], d["c"], d["a"]; dl = y - x; n = len(x); te = rng.permutation(n)[: n // 20]; tr = np.setdiff1d(np.arange(n), te)
mu_x, sd_x = x[tr].mean(0), x[tr].std(0) + 1e-3; mu_d, sd_d = dl[tr].mean(0), dl[tr].std(0) + 1e-3
cond = np.concatenate([(x - mu_x) / sd_x, c, a], 1).astype(np.float32); Z = torch.tensor((dl - mu_d) / sd_d, dtype=torch.float32, device=dev); CC = torch.tensor(cond, device=dev)
D = Z.shape[1]; wm = mlp(D + 1 + CC.shape[1], D); opt = torch.optim.AdamW(wm.parameters(), 3e-4, weight_decay=1e-4); trt = torch.tensor(tr, device=dev)
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, int(sys.argv[4]) if len(sys.argv) > 4 else 60000)
for it in range(int(sys.argv[4]) if len(sys.argv) > 4 else 60000):
    b = trt[torch.randint(len(trt), (8192,), device=dev)]; z1 = Z[b]; z0 = torch.randn_like(z1); t = torch.rand(len(b), 1, device=dev)
    loss = ((wm(torch.cat([(1 - t) * z0 + t * z1, t, CC[b]], 1)) - (z1 - z0)) ** 2).mean(); opt.zero_grad(); loss.backward(); opt.step(); sched.step()
    if it % 5000 == 0: print("wm", it, loss.item(), flush=True)
with torch.no_grad():
    cb = CC[torch.tensor(te, device=dev)]; z = torch.randn(len(cb), D, device=dev)
    for k in range(10): z = z + wm(torch.cat([z, torch.full((len(cb), 1), k / 10, device=dev), cb], 1)) / 10
    pred = z.cpu().numpy() * sd_d + mu_d
print("world-model held-out MAE", float(np.abs(pred - dl[te]).mean()), "no-change", float(np.abs(dl[te]).mean()))
# ---- value model
vx, vc, va, vm = d["vx"], d["vc"], d["va"], d["vm"]; nv = len(vx); vte = rng.permutation(nv)[: nv // 20]; vtr = np.setdiff1d(np.arange(nv), vte)
vin = np.concatenate([(vx - mu_x) / sd_x, vc, va], 1).astype(np.float32); vmu, vsd = vm[vtr].mean(0), vm[vtr].std(0) + 1e-3
VI = torch.tensor(vin, device=dev); VT = torch.tensor((vm - vmu) / vsd, dtype=torch.float32, device=dev); vtrt = torch.tensor(vtr, device=dev)
vn = mlp(VI.shape[1], 2); vopt = torch.optim.AdamW(vn.parameters(), 3e-4, weight_decay=1e-4)
for it in range(30000):
    b = vtrt[torch.randint(len(vtrt), (8192,), device=dev)]; loss = ((vn(VI[b]) - VT[b]) ** 2).mean(); vopt.zero_grad(); loss.backward(); vopt.step()
    if it % 5000 == 0: print("value", it, loss.item(), flush=True)
with torch.no_grad(): vp = vn(VI[torch.tensor(vte, device=dev)]).cpu().numpy() * vsd + vmu
r2 = 1 - ((vp - vm[vte]) ** 2).mean(0) / vm[vte].var(0); print("value R2 (margin, money):", r2.tolist())
json.dump({"agents": agents, "wm": {"W": export(wm), "mu_x": mu_x.tolist(), "sd_x": sd_x.tolist(), "mu_d": mu_d.tolist(), "sd_d": sd_d.tolist()},
           "value": {"W": export(vn), "mu": vmu.tolist(), "sd": vsd.tolist()}}, open(out, "w"))
print("saved", out)
