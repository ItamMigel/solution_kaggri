"""Train BC v3 (single-expert): board ResNet trunk -> unit heads (op, qty, target cell) + autoregressive market decoder.
usage: python train3.py --data ../../../../bc3_data/boey --out ../../../../bc3_runs/boey_r1 --epochs 30"""
import argparse, glob, json, os, sys, time
import numpy as np, torch, torch.nn as nn, torch.nn.functional as Fn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feat3 as F  # noqa: E402

IGN = F.IGNORE


def load(root, val_eps=12, seed=0):
    fs = sorted(glob.glob(f"{root}/*.npz")); rng = np.random.default_rng(seed); rng.shuffle(fs)
    parts = {"val": fs[:val_eps], "train": fs[val_eps:]}; out = {}
    for split, lst in parts.items():
        cols = {k: [] for k in ("B", "G", "MS", "MT", "MQ", "ut", "ui", "ux", "uy", "uv", "ua", "uq", "tx", "ty")}; off = 0
        for f in lst:
            d = np.load(f); T = len(d["G"])
            for k in cols:
                cols[k].append(d[k] + off if k == "ut" else d[k])
            off += T
        o = {k: np.concatenate(v) for k, v in cols.items()}
        o["tc"] = o["ty"].astype(np.int64) * 10 + o["tx"].astype(np.int64)
        o["ustart"] = np.searchsorted(o["ut"], np.arange(len(o["G"]) + 1))
        o["files"] = [os.path.basename(f) for f in lst]
        out[split] = o; print(split, len(lst), "eps", len(o["G"]), "steps", len(o["ua"]), "units", flush=True)
    return out


def to_dev(D, dev):
    t = {}
    t["B"] = torch.from_numpy(D["B"]).to(dev)  # fp16
    for k in ("G", "uv", "MS"):
        t[k] = torch.from_numpy(D[k]).to(dev)
    for k in ("MT", "MQ", "ut", "ui", "ux", "uy", "ua", "uq", "tc"):
        t[k] = torch.from_numpy(D[k].astype(np.int64)).to(dev)
    t["ustart"] = torch.from_numpy(D["ustart"]).to(dev)
    return t


class Res(nn.Module):
    def __init__(s, c):
        super().__init__(); s.a = nn.Conv2d(c, c, 3, padding=1); s.b = nn.Conv2d(c, c, 3, padding=1)

    def forward(s, x):
        return Fn.relu(x + s.b(Fn.relu(s.a(x))))


class Net(nn.Module):
    def __init__(s, ch=128, blocks=8, hid=256):
        super().__init__()
        s.cfg = dict(ch=ch, blocks=blocks, hid=hid)
        s.inp = nn.Conv2d(F.C_BOARD + F.G_DIM, ch, 3, padding=1)
        s.body = nn.Sequential(*[Res(ch) for _ in range(blocks)])
        uin = ch + F.U_DIM + F.G_DIM
        s.unit = nn.Sequential(nn.Linear(uin, hid), nn.ReLU(), nn.Linear(hid, hid), nn.ReLU())
        s.u_op = nn.Linear(hid, len(F.UNIT_OPS)); s.u_q = nn.Linear(hid + len(F.UNIT_OPS), len(F.QTY_VALS))
        s.tq = nn.Sequential(nn.Linear(uin, hid), nn.ReLU(), nn.Linear(hid, ch))
        s.m_ctx = nn.Sequential(nn.Linear(2 * ch + F.G_DIM + F.MS_DIM, hid), nn.ReLU(), nn.Linear(hid, hid), nn.Tanh())
        s.m_tok_emb = nn.Embedding(F.N_TOK + 1, 48)  # index N_TOK = <start>
        s.m_q_emb = nn.Embedding(F.QMAX + 1, 16)     # index QMAX = no qty
        s.m_slot_emb = nn.Embedding(F.N_SLOTS, 16)
        s.m_gru = nn.GRUCell(48 + 16 + 16 + hid, hid)
        s.m_tok = nn.Linear(hid, F.N_TOK)
        s.m_q = nn.Sequential(nn.Linear(hid + 48, hid), nn.ReLU(), nn.Linear(hid, F.QMAX))

    def trunk(s, B, G):
        x = torch.cat([B.float(), G[:, :, None, None].expand(-1, -1, 10, 10)], 1)
        return s.body(Fn.relu(s.inp(x)))

    def units(s, h, G, bi, ux, uy, uv, op_for_q=None):
        z0 = torch.cat([h[bi, :, uy, ux], uv, G[bi]], 1)
        z = s.unit(z0); opl = s.u_op(z)
        oh = Fn.one_hot(op_for_q, len(F.UNIT_OPS)).float() if op_for_q is not None else Fn.softmax(opl, 1)
        ql = s.u_q(torch.cat([z, oh], 1))
        tl = torch.einsum("uc,ucp->up", s.tq(z0), h.flatten(2)[bi]) / (h.shape[1] ** 0.5)
        return opl, ql, tl

    def m_context(s, h, G, MS):
        return s.m_ctx(torch.cat([h.mean((2, 3)), h.amax((2, 3)), G, MS], 1))

    def m_step(s, state, ctx, prev_tok, prev_q, slot):
        x = torch.cat([s.m_tok_emb(prev_tok), s.m_q_emb(prev_q), s.m_slot_emb(slot), ctx], 1)
        state = s.m_gru(x, state)
        return state, s.m_tok(state)

    def m_qty(s, state, tok):
        return s.m_q(torch.cat([state, s.m_tok_emb(tok)], 1))

    def market_tf(s, h, G, MS, MT, MQ):
        """teacher-forced logits: tok [B,S,N_TOK], qty [B,S,QMAX]"""
        Bn = G.shape[0]; ctx = s.m_context(h, G, MS); state = ctx
        prev_t = torch.full((Bn,), F.N_TOK, dtype=torch.long, device=G.device)
        prev_q = torch.full((Bn,), F.QMAX, dtype=torch.long, device=G.device)
        tl, ql = [], []
        for sl in range(F.N_SLOTS):
            slot = torch.full((Bn,), sl, dtype=torch.long, device=G.device)
            state, logit = s.m_step(state, ctx, prev_t, prev_q, slot); tl.append(logit)
            cur = MT[:, sl].clamp(min=0); ql.append(s.m_qty(state, cur))
            prev_t = cur; prev_q = torch.where(MQ[:, sl] >= 0, MQ[:, sl], torch.full_like(MQ[:, sl], F.QMAX))
        return torch.stack(tl, 1), torch.stack(ql, 1)


def gather_units(T, idx):
    st = T["ustart"][idx]; en = T["ustart"][idx + 1]; cnt = en - st
    bi = torch.repeat_interleave(torch.arange(len(idx), device=idx.device), cnt)
    ui = torch.repeat_interleave(st, cnt) + (torch.arange(int(cnt.sum()), device=idx.device) - torch.repeat_interleave(torch.cumsum(cnt, 0) - cnt, cnt))
    return bi, ui


def losses(net, T, idx):
    B = T["B"][idx]; G = T["G"][idx]; h = net.trunk(B, G)
    bi, ui = gather_units(T, idx)
    ua = T["ua"][ui]; uq = T["uq"][ui]; tc = T["tc"][ui]
    opl, ql, tl = net.units(h, G, bi, T["ux"][ui], T["uy"][ui], T["uv"][ui], op_for_q=ua)
    lu = Fn.cross_entropy(opl, ua); lt = Fn.cross_entropy(tl, tc)
    lq = Fn.cross_entropy(ql, uq, ignore_index=IGN) if (uq >= 0).any() else opl.sum() * 0
    MT = T["MT"][idx]; MQ = T["MQ"][idx]
    mtl, mql = net.market_tf(h, G, T["MS"][idx], MT, MQ)
    lmt = Fn.cross_entropy(mtl.reshape(-1, F.N_TOK), MT.reshape(-1), ignore_index=IGN)
    lmq = Fn.cross_entropy(mql.reshape(-1, F.QMAX), MQ.reshape(-1), ignore_index=IGN)
    stats = dict(u_ok=(opl.argmax(1) == ua).float().sum(), u_n=float(len(ua)), t_ok=(tl.argmax(1) == tc).float().sum(),
                 q_ok=((ql.argmax(1) == uq) & (uq >= 0)).float().sum(), q_n=(uq >= 0).float().sum(),
                 mt_ok=((mtl.argmax(2) == MT) & (MT >= 0)).float().sum(), mt_n=(MT >= 0).float().sum(),
                 mq_ok=((mql.argmax(2) == MQ) & (MQ >= 0)).float().sum(), mq_n=(MQ >= 0).float().sum(),
                 m_exact=(((mtl.argmax(2) == MT) | (MT < 0)).all(1) & ((mql.argmax(2) == MQ) | (MQ < 0)).all(1)).float().sum(),
                 steps=float(len(idx)))
    return lu + lt + lq + lmt + 0.5 * lmq, dict(lu=lu, lt=lt, lq=lq, lmt=lmt, lmq=lmq), stats


def evaluate(net, T, bs=512):
    net.eval(); acc = {}
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        n = len(T["G"])
        for s0 in range(0, n, bs):
            idx = torch.arange(s0, min(n, s0 + bs), device=T["G"].device)
            _, _, st = losses(net, T, idx)
            for k, v in st.items():
                acc[k] = acc.get(k, 0.0) + float(v)
    net.train()
    return dict(unit_acc=acc["u_ok"] / acc["u_n"], target_acc=acc["t_ok"] / acc["u_n"], qty_acc=acc["q_ok"] / max(1, acc["q_n"]),
                mkt_tok_acc=acc["mt_ok"] / acc["mt_n"], mkt_qty_acc=acc["mq_ok"] / max(1, acc["mq_n"]), mkt_exact=acc["m_exact"] / acc["steps"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--data", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=30); ap.add_argument("--bs", type=int, default=256); ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--ch", type=int, default=128); ap.add_argument("--blocks", type=int, default=8); ap.add_argument("--hid", type=int, default=256)
    ap.add_argument("--val-eps", type=int, default=12); ap.add_argument("--wd", type=float, default=1e-4); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); dev = "cuda"; torch.manual_seed(a.seed)
    D = load(a.data, a.val_eps, a.seed); TR = to_dev(D["train"], dev); VA = to_dev(D["val"], dev)
    json.dump({"val_files": D["val"]["files"], "args": vars(a)}, open(f"{a.out}/split.json", "w"))
    net = Net(a.ch, a.blocks, a.hid).to(dev)
    decay = [p for n_, p in net.named_parameters() if p.ndim > 1 and "emb" not in n_]
    no_decay = [p for n_, p in net.named_parameters() if not (p.ndim > 1 and "emb" not in n_)]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": a.wd}, {"params": no_decay, "weight_decay": 0.0}], a.lr)
    n = len(TR["G"]); spe = n // a.bs; sched = torch.optim.lr_scheduler.OneCycleLR(opt, a.lr, total_steps=a.epochs * spe, pct_start=0.1)
    log = open(f"{a.out}/log.jsonl", "w"); best = -1
    for ep in range(a.epochs):
        t0 = time.time(); perm = torch.randperm(n, device=dev); agg = {}
        for s0 in range(0, spe * a.bs, a.bs):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                loss, parts, _ = losses(net, TR, perm[s0:s0 + a.bs])
            opt.zero_grad(set_to_none=True); loss.backward(); nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step(); sched.step()
            for k, v in parts.items():
                agg[k] = agg.get(k, 0.0) + float(v.detach())
        ev = evaluate(net, VA); rec = dict(epoch=ep, secs=round(time.time() - t0), **{k: round(v / spe, 4) for k, v in agg.items()}, **{k: round(v, 4) for k, v in ev.items()})
        print(json.dumps(rec), flush=True); log.write(json.dumps(rec) + "\n"); log.flush()
        ck = {"state": net.state_dict(), "cfg": net.cfg, "feat": dict(C_BOARD=F.C_BOARD, G_DIM=F.G_DIM, U_DIM=F.U_DIM), "epoch": ep, "ev": ev}
        torch.save(ck, f"{a.out}/last.pt")
        score = ev["unit_acc"] + ev["target_acc"] + ev["mkt_exact"]
        if score > best:
            best = score; torch.save(ck, f"{a.out}/best.pt")
