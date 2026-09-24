"""Train team-conditioned BC policy (board ResNet -> unit action head + market head).
usage: python train.py --data mmpq,dsm,mgoose --out /workspace/shared/bc_runs/v1 --epochs 20"""
import argparse, glob, json, os, sys, time
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feat
TEAMS = ["mmpq", "dsm", "mgoose"]

def load(teams, root=os.environ.get("BC_DATA", "/workspace/shared/bc_data"), val_frac=0.1, seed=0):
    rng = np.random.default_rng(seed); parts = {"train": [], "val": []}
    for ti, t in enumerate(teams):
        fs = sorted(glob.glob(f"{root}/{t}/*.npz")); rng.shuffle(fs)
        nv = max(2, int(len(fs) * val_frac))
        for k, f in enumerate(fs):
            parts["val" if k < nv else "train"].append((ti, f))
    out = {}
    for split, lst in parts.items():
        Bs, Gs, Qs, UT, UX, UY, UV, UA, W = [], [], [], [], [], [], [], [], []; TX, TY = [], []; off = 0
        for ti, f in lst:
            d = np.load(f); T = len(d["G"])
            team = np.zeros((T, len(TEAMS)), np.float32); team[:, TEAMS.index(teams[ti])] = 1
            Bs.append(d["B"]); Gs.append(np.concatenate([d["G"], team], 1)); Qs.append(d["Q"])
            UT.append(d["ut"] + off); UX.append(d["ux"]); UY.append(d["uy"]); UV.append(d["uv"]); UA.append(d["ua"]); TX.append(d["tx"]); TY.append(d["ty"])
            W.append(np.full(T, 1.0 if bool(d["won"]) else 0.3, np.float32)); off += T
        o = dict(B=np.concatenate(Bs), G=np.concatenate(Gs), Q=np.concatenate(Qs).astype(np.int64), ut=np.concatenate(UT),
                 ux=np.concatenate(UX).astype(np.int64), uy=np.concatenate(UY).astype(np.int64), uv=np.concatenate(UV), ua=np.concatenate(UA).astype(np.int64), w=np.concatenate(W),
                 tc=(np.concatenate(TY).astype(np.int64) * 10 + np.concatenate(TX).astype(np.int64)))
        start = np.searchsorted(o["ut"], np.arange(len(o["G"]) + 1)); o["ustart"] = start
        out[split] = o; print(split, len(lst), "eps", len(o["G"]), "steps", len(o["ua"]), "units", flush=True)
    return out

class Res(nn.Module):
    def __init__(s, c):
        super().__init__(); s.a = nn.Conv2d(c, c, 3, padding=1); s.b = nn.Conv2d(c, c, 3, padding=1)
    def forward(s, x): return F.relu(x + s.b(F.relu(s.a(x))))

class Net(nn.Module):
    def __init__(s, gdim, ch=96, blocks=6):
        super().__init__()
        s.inp = nn.Conv2d(feat.C_BOARD + gdim, ch, 3, padding=1); s.body = nn.Sequential(*[Res(ch) for _ in range(blocks)])
        s.unit = nn.Sequential(nn.Linear(ch + feat.U_DIM + gdim, 192), nn.ReLU(), nn.Linear(192, len(feat.UNIT_OPS)))
        s.tq = nn.Sequential(nn.Linear(ch + feat.U_DIM + gdim, 192), nn.ReLU(), nn.Linear(192, ch))
        s.mkt = nn.Sequential(nn.Linear(2 * ch + gdim, 384), nn.ReLU(), nn.Linear(384, len(feat.MKT_KEYS) * (feat.MKT_MAX + 1)))
    def trunk(s, B, G):
        x = torch.cat([B, G[:, :, None, None].expand(-1, -1, 10, 10)], 1)
        return s.body(F.relu(s.inp(x)))
    def forward(s, B, G, bi, ux, uy, uv):
        h = s.trunk(B, G)
        hu = h[bi, :, uy, ux]
        uin = torch.cat([hu, uv, G[bi]], 1); ul = s.unit(uin)
        tl = torch.einsum("uc,ucp->up", s.tq(uin), h.flatten(2)[bi]) / (h.shape[1] ** 0.5)
        pooled = torch.cat([h.mean((2, 3)), h.amax((2, 3)), G], 1)
        ml = s.mkt(pooled).view(-1, len(feat.MKT_KEYS), feat.MKT_MAX + 1)
        return ul, ml, tl

def batch(D, idx, dev):
    B = torch.from_numpy(D["B"][idx].astype(np.float32)).to(dev); G = torch.from_numpy(D["G"][idx]).to(dev)
    Q = torch.from_numpy(D["Q"][idx]).to(dev); W = torch.from_numpy(D["w"][idx]).to(dev)
    us = [np.arange(D["ustart"][i], D["ustart"][i + 1]) for i in idx]
    bi = np.concatenate([np.full(len(u), k) for k, u in enumerate(us)]); ui = np.concatenate(us)
    t = lambda a: torch.from_numpy(a).to(dev)
    return B, G, Q, W, t(bi), t(D["ux"][ui]), t(D["uy"][ui]), t(D["uv"][ui]), t(D["ua"][ui]), t(D["tc"][ui])

def evaluate(net, D, dev, bs=512):
    net.eval(); uc = un = 0; mc = mn = 0; mall = 0; tcc = 0
    with torch.no_grad():
        for s in range(0, len(D["G"]), bs):
            idx = np.arange(s, min(len(D["G"]), s + bs))
            B, G, Q, W, bi, ux, uy, uv, ua, tc = batch(D, idx, dev)
            ul, ml, tl = net(B, G, bi, ux, uy, uv)
            uc += (ul.argmax(1) == ua).sum().item(); un += len(ua); tcc += (tl.argmax(1) == tc).sum().item()
            mp = ml.argmax(2); mc += (mp == Q).sum().item(); mn += Q.numel(); mall += (mp == Q).all(1).sum().item()
    net.train(); return dict(unit_acc=uc / un, target_acc=tcc / un, mkt_key_acc=mc / mn, mkt_exact=mall / len(D["G"]))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--data", default="mmpq,dsm,mgoose"); ap.add_argument("--out", required=True)
    ap.add_argument("--root", default=os.environ.get("BC_DATA", "/workspace/shared/bc_data")); ap.add_argument("--epochs", type=int, default=20); ap.add_argument("--bs", type=int, default=256); ap.add_argument("--lr", type=float, default=1e-3)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); dev = "cuda"
    D = load(a.data.split(","), root=a.root); gdim = D["train"]["G"].shape[1]
    net = Net(gdim).to(dev); opt = torch.optim.AdamW(net.parameters(), a.lr, weight_decay=1e-4)
    n = len(D["train"]["G"]); steps = a.epochs * (n // a.bs); sched = torch.optim.lr_scheduler.OneCycleLR(opt, a.lr, total_steps=steps)
    log = open(f"{a.out}/log.jsonl", "w"); it = 0; best = -1
    for ep in range(a.epochs):
        perm = np.random.permutation(n); t0 = time.time()
        for s in range(0, n - a.bs + 1, a.bs):
            B, G, Q, W, bi, ux, uy, uv, ua, tc = batch(D["train"], perm[s:s + a.bs], dev)
            ul, ml, tl = net(B, G, bi, ux, uy, uv)
            lt = (F.cross_entropy(tl, tc, reduction="none") * W[bi]).mean()
            lu = (F.cross_entropy(ul, ua, reduction="none") * W[bi]).mean()
            lm = (F.cross_entropy(ml.reshape(-1, feat.MKT_MAX + 1), Q.reshape(-1), reduction="none").view(Q.shape).sum(1) * W).mean()
            loss = lu + lt + 0.3 * lm; opt.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step(); sched.step(); it += 1
        ev = evaluate(net, D["val"], dev); rec = dict(epoch=ep, lu=lu.item(), lm=lm.item(), secs=round(time.time() - t0), **ev)
        print(json.dumps(rec), flush=True); log.write(json.dumps(rec) + "\n"); log.flush()
        if ev["unit_acc"] + ev["target_acc"] > best:
            best = ev["unit_acc"] + ev["target_acc"]; torch.save({"state": net.state_dict(), "gdim": gdim, "teams": TEAMS}, f"{a.out}/best.pt")
