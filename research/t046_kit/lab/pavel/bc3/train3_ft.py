"""T045 fine-tune variant of Pavel's train3.py (--init, fixed team order, episode-level split).
Train BC v3 (single-expert): board ResNet trunk -> unit heads (op, qty, target cell) + autoregressive market decoder.
usage: python train3.py --data ../../../../bc3_data/boey --out ../../../../bc3_runs/boey_r1 --epochs 30"""
import argparse, glob, json, os, sys, time
import numpy as np, torch, torch.nn as nn, torch.nn.functional as Fn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feat3 as F  # noqa: E402

IGN = F.IGNORE


def _ep_id(f):
    import re
    m = re.search(r"(\d{6,})", os.path.basename(f)); return m.group(1) if m else os.path.basename(f)


def load(root, val_eps=12, seed=0, team_order=None, split_seed=None, val_ids=None):
    """root: one dir, or comma-separated dirs (multi-team: a team one-hot is appended to G, team = dir basename).
    T045: team_order fixes the one-hot slot order (must equal the init checkpoint's cfg['teams']); several dirs may map to
    the same team via 'dir=team'. The val split is by EPISODE ID across all dirs (both seats of an episode together),
    using split_seed (independent of the init seed) or an explicit val_ids set."""
    specs = []
    for r in root.split(","):
        d, _, t = r.partition("="); specs.append((d, t or os.path.basename(d.rstrip("/"))))
    teams = list(team_order) if team_order else list(dict.fromkeys(t for _, t in specs))
    multi = len(teams) > 1; roots = teams; parts = {"val": [], "train": []}
    allf = [(teams.index(t), f) for d, t in specs for f in sorted(glob.glob(f"{d}/*.npz"))]
    if val_ids is None:
        eps = sorted({_ep_id(f) for _, f in allf}); rng = np.random.default_rng(seed if split_seed is None else split_seed); rng.shuffle(eps)
        val_ids = set(eps[: val_eps * max(1, len(specs))])
    for ti, f in allf:
        parts["val" if _ep_id(f) in val_ids else "train"].append((ti, f))
    out = {}
    for split, lst in parts.items():
        keys = ("B", "G", "MS", "MT", "MQ", "ut", "ui", "ux", "uy", "uv", "ua", "uq", "tx", "ty")
        step_keys = {"B", "G", "MS", "MT", "MQ"}
        # pass 1: sizes and dtypes (reads only small arrays); pass 2: fill preallocated arrays (no 2x concatenate peak)
        sizes = []; proto = {}
        for ti, f in lst:
            d = np.load(f); sizes.append((len(d["G"]), len(d["ut"])))
            if not proto:
                for k in keys:
                    a = d[k]; proto[k] = (a.shape[1:], a.dtype)
        NT = sum(s[0] for s in sizes); NU = sum(s[1] for s in sizes)
        o = {}
        for k in keys:
            shp, dt = proto[k]
            if k == "G" and multi:
                shp = (shp[0] + len(teams),)
            o[k] = np.empty(((NT if k in step_keys else NU),) + tuple(shp), dt)
        off = 0; uoff = 0
        for (ti, f), (T, U) in zip(lst, sizes):
            d = np.load(f)
            for k in keys:
                v = d[k]
                if k == "ut":
                    v = v + off
                if k == "G" and multi:
                    oh = np.zeros((T, len(teams)), np.float32); oh[:, ti] = 1; v = np.concatenate([v, oh], 1)
                if k in step_keys:
                    o[k][off:off + T] = v
                else:
                    o[k][uoff:uoff + U] = v
            off += T; uoff += U
        o["tc"] = o["ty"].astype(np.int64) * 10 + o["tx"].astype(np.int64)
        o["ustart"] = np.searchsorted(o["ut"], np.arange(len(o["G"]) + 1))
        o["files"] = [os.path.basename(f) for _, f in lst]; o["file_team"] = [ti for ti, _ in lst]; o["file_steps"] = [s[0] for s in sizes]
        o["teams"] = list(teams) if multi else []
        out[split] = o; print(split, len(lst), "eps", len(o["G"]), "steps", len(o["ua"]), "units", flush=True)
    return out


def to_dev(D, dev, cpu_board=False):
    t = {}
    # fp16 boards; with cpu_board they stay in pinned host memory and only the batch is copied (large multi-team data)
    if cpu_board:
        try:
            t["B"] = torch.from_numpy(D["B"]).pin_memory()
        except RuntimeError:  # page-locked host memory exhausted (e.g. another run pinned its boards): use pageable memory
            t["B"] = torch.from_numpy(D["B"])
    else:
        t["B"] = torch.from_numpy(D["B"]).to(dev)
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
    def __init__(s, ch=128, blocks=8, hid=256, u_dim=None, g_dim=None, teams=None, uext=None):
        super().__init__()
        u_dim = u_dim or F.U_DIM_V1; g_dim = g_dim or F.G_DIM
        if uext is None:  # older checkpoints: extra unit dims could only be motion
            uext = ["motion"] if u_dim > F.U_DIM_V1 else []
        s.cfg = dict(ch=ch, blocks=blocks, hid=hid, u_dim=u_dim, g_dim=g_dim, teams=list(teams or []), uext=list(uext))
        s.inp = nn.Conv2d(F.C_BOARD + g_dim, ch, 3, padding=1)
        s.body = nn.Sequential(*[Res(ch) for _ in range(blocks)])
        uin = ch + u_dim + g_dim
        s.unit = nn.Sequential(nn.Linear(uin, hid), nn.ReLU(), nn.Linear(hid, hid), nn.ReLU())
        s.u_op = nn.Linear(hid, len(F.UNIT_OPS)); s.u_q = nn.Linear(hid + len(F.UNIT_OPS), len(F.QTY_VALS))
        s.tq = nn.Sequential(nn.Linear(uin, hid), nn.ReLU(), nn.Linear(hid, ch))
        s.m_ctx = nn.Sequential(nn.Linear(2 * ch + g_dim + F.MS_DIM, hid), nn.ReLU(), nn.Linear(hid, hid), nn.Tanh())
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
    B = T["B"][idx] if T["B"].device == idx.device else T["B"][idx.cpu()].to(idx.device, non_blocking=True)
    G = T["G"][idx]; h = net.trunk(B, G)
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
    ap.add_argument("--cpu-board", action="store_true", help="keep boards in pinned host memory (datasets larger than GPU memory)")
    ap.add_argument("--init", default="", help="T045: weight-only warm start from this best.pt (same cfg/teams); fine-tune")
    ap.add_argument("--split-seed", type=int, default=None, help="T045: val split seed, independent of --seed")
    ap.add_argument("--pct-start", type=float, default=0.1)
    ap.add_argument("--fresh-frac", type=float, default=-1, help="T046: share of minibatch steps drawn from fresh files (f_*.npz); -1 = natural mix")
    ap.add_argument("--val-ids", default="", help="T046: file with one episode id per line = fixed validation split (overrides --split-seed)")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); dev = "cuda"; torch.manual_seed(a.seed)
    init = torch.load(a.init, map_location="cpu", weights_only=False) if a.init else None
    if init is not None:  # architecture always from the init checkpoint
        a.ch, a.blocks, a.hid = init["cfg"]["ch"], init["cfg"]["blocks"], init["cfg"]["hid"]
    vids = {l.strip() for l in open(a.val_ids) if l.strip()} if a.val_ids else None
    D = load(a.data, a.val_eps, a.seed, team_order=(init["cfg"]["teams"] if init else None), split_seed=a.split_seed, val_ids=vids); TR = to_dev(D["train"], dev, a.cpu_board); VA = to_dev(D["val"], dev, a.cpu_board)
    json.dump({"val_files": D["val"]["files"], "val_file_team": D["val"]["file_team"], "teams": D["val"]["teams"], "args": vars(a)},
              open(f"{a.out}/split.json", "w"))
    f0 = np.load(sorted(glob.glob(f"{a.data.split(',')[0].partition('=')[0]}/*.npz"))[0])
    uext = [str(x) for x in f0["uext"]] if "uext" in f0 else None
    net = Net(a.ch, a.blocks, a.hid, u_dim=D["train"]["uv"].shape[1], g_dim=D["train"]["G"].shape[1], teams=D["train"]["teams"], uext=uext).to(dev)
    if init is not None:
        assert init["cfg"]["teams"] == net.cfg["teams"] and init["cfg"]["g_dim"] == net.cfg["g_dim"] and init["cfg"]["u_dim"] == net.cfg["u_dim"], (init["cfg"], net.cfg)
        net.load_state_dict(init["state"]); print("init from", a.init, "epoch", init.get("epoch"), "ev", init.get("ev"), flush=True)
        print(json.dumps({"epoch": -1, **evaluate(net, VA)}), flush=True)
    decay = [p for n_, p in net.named_parameters() if p.ndim > 1 and "emb" not in n_]
    no_decay = [p for n_, p in net.named_parameters() if not (p.ndim > 1 and "emb" not in n_)]
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": a.wd}, {"params": no_decay, "weight_decay": 0.0}], a.lr)
    n = len(TR["G"]); spe = n // a.bs; sched = torch.optim.lr_scheduler.OneCycleLR(opt, a.lr, total_steps=a.epochs * spe, pct_start=a.pct_start)
    step_w = None
    if a.fresh_frac >= 0:
        fresh_file = np.array([os.path.basename(f).startswith("f_") for f in D["train"]["files"]])
        lens = np.array(D["train"]["file_steps"]); is_f = np.repeat(fresh_file, lens)
        nf, no = int(is_f.sum()), int((~is_f).sum()); assert nf > 0 and no > 0, (nf, no)
        w = np.where(is_f, a.fresh_frac / nf, (1 - a.fresh_frac) / no)
        step_w = torch.tensor(w, dtype=torch.float32, device=dev)
        print(json.dumps({"fresh_steps": nf, "old_steps": no, "fresh_frac": a.fresh_frac, "natural_frac": round(nf / (nf + no), 3)}), flush=True)
    log = open(f"{a.out}/log.jsonl", "w"); best = -1
    for ep in range(a.epochs):
        t0 = time.time(); agg = {}
        if step_w is None:
            perm = torch.randperm(n, device=dev)
        else:
            perm = torch.multinomial(step_w, spe * a.bs, replacement=True)
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
        torch.save(ck, f"{a.out}/e{ep + 1}.pt")
        score = ev["unit_acc"] + ev["target_acc"] + ev["mkt_exact"]
        if score > best:
            best = score; torch.save(ck, f"{a.out}/best.pt")
