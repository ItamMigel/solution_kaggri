"""PPO fine-tuning of the BC policy in the exact batched gpuenv (self-play, both seats use the current policy).
usage: python ppo.py --init /workspace/shared/bc_runs/v2/final.pt --out /workspace/shared/bcppo_runs/r1 --envs 256 --iters 50
Reward per player: dense d(money)/1e4 each step + terminal margin/1e4 * --margin-coef.  GAE(gamma, lam).
Loss: clipped PPO + value + entropy bonus + KL(BC || pi) anchor (annealed)."""
import argparse, copy, json, os, sys, time
import torch, torch.nn.functional as F
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import policy, gpufeat
from gpuenv.env import VecKaggriculture

REC_KEYS = ("board", "G", "uv", "ux", "uy", "umask", "opm", "t", "o", "mb", "hire_max", "land_max", "minc")


def rollout(net, ve, B, dev, team, seed_base, greedy=False):
    st = ve.reset(torch.arange(B, device=dev) + seed_base); so = gpufeat.ShopOrder(B, dev)
    T = 719; buf = {p: {k: [] for k in REC_KEYS + ("logp", "v", "r")} for p in (0, 1)}
    prev = st.money.float().clone()
    with torch.no_grad():
        for t in range(T):
            so.update(st)
            outs = [policy.act(net, st, p, so, team, greedy=greedy) for p in (0, 1)]
            st, _, done, info = ve.step(st, policy.combine(outs[0][0], outs[1][0]))
            money = st.money.float(); dm = (money - prev) / 1e4; prev = money.clone()
            for p in (0, 1):
                a, lp, v, ent, rec = outs[p]
                for k in REC_KEYS: buf[p][k].append(rec[k])
                buf[p]["logp"].append(lp); buf[p]["v"].append(v); buf[p]["r"].append(dm[:, p])
    final = st.money.float()
    return buf, final


def gae(r, v, gamma, lam):
    T = r.shape[0]; adv = torch.zeros_like(r); last = torch.zeros_like(r[0])
    for t in reversed(range(T)):
        nv = v[t + 1] if t + 1 < T else torch.zeros_like(v[t])
        delta = r[t] + gamma * nv - v[t]; last = delta + gamma * lam * last; adv[t] = last
    return adv, adv + v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", required=True); ap.add_argument("--out", required=True); ap.add_argument("--envs", type=int, default=256)
    ap.add_argument("--iters", type=int, default=50); ap.add_argument("--lr", type=float, default=3e-5); ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--mb", type=int, default=8192); ap.add_argument("--gamma", type=float, default=0.999); ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--clip", type=float, default=0.2); ap.add_argument("--ent", type=float, default=0.001); ap.add_argument("--kl", type=float, default=0.05)
    ap.add_argument("--margin-coef", type=float, default=0.5); ap.add_argument("--team", default="dsm"); ap.add_argument("--vf", type=float, default=0.5)
    ap.add_argument("--device", default="cuda"); ap.add_argument("--amp", default="none", choices=["none", "bf16"])
    ap.add_argument("--resume", action="store_true", help="continue from <out>/last.pt if present"); ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True); dev = a.device
    torch.manual_seed(a.seed)
    if a.amp == "bf16": policy.AMP = torch.bfloat16
    ck = torch.load(a.init, map_location=dev)
    net = policy.PolicyNet(ck["gdim"]).to(dev); net.load_state_dict(ck["state"], strict=False)
    start = 0
    if a.resume and os.path.exists(f"{a.out}/last.pt"):
        lk = torch.load(f"{a.out}/last.pt", map_location=dev); net.load_state_dict(lk["state"]); start = lk["iter"] + 1; print("resumed at iter", start, flush=True)
    json.dump(vars(a), open(f"{a.out}/args.json", "w"), indent=1)
    bc = policy.PolicyNet(ck["gdim"]).to(dev); bc.load_state_dict(ck["state"], strict=False); bc.eval()
    for q in bc.parameters(): q.requires_grad_(False)
    teams = ck.get("teams", ["mmpq", "dsm", "mgoose"]); team = torch.zeros((1, len(teams)), device=dev); team[0, teams.index(a.team)] = 1
    opt = torch.optim.Adam(net.parameters(), lr=a.lr); ve = VecKaggriculture(a.envs, device=dev)
    log = open(f"{a.out}/log.jsonl", "a")
    for it in range(start, a.iters):
        t0 = time.time(); net.eval()
        buf, final = rollout(net, ve, a.envs, dev, team, seed_base=1_000_003 * (it + 1) + 7_919 * a.seed)
        t_roll = time.time() - t0
        margin = final[:, 0] - final[:, 1]
        data = {k: [] for k in REC_KEYS + ("logp", "adv", "ret", "v")}
        for p in (0, 1):
            r = torch.stack(buf[p]["r"]); v = torch.stack(buf[p]["v"])
            r[-1] += a.margin_coef * (margin if p == 0 else -margin) / 1e4
            adv, ret = gae(r, v, a.gamma, a.lam)
            for k in REC_KEYS: data[k].append(torch.stack(buf[p][k]).flatten(0, 1))
            data["logp"].append(torch.stack(buf[p]["logp"]).flatten(0, 1)); data["adv"].append(adv.flatten()); data["ret"].append(ret.flatten()); data["v"].append(v.flatten())
        del buf
        data = {k: torch.cat(v) for k, v in data.items()}
        adv = data["adv"]; data["adv"] = (adv - adv.mean()) / (adv.std() + 1e-8)
        N = data["adv"].shape[0]; net.train(); stats = []
        for ep in range(a.epochs):
            perm = torch.randperm(N, device=dev)
            for s in range(0, N, a.mb):
                idx = perm[s:s + a.mb]; rec = {k: data[k][idx] for k in REC_KEYS}
                board = rec["board"].float(); ux = rec["ux"].long(); uy = rec["uy"].long()
                ul, tl, ml, v = net.full(board, rec["G"], rec["uv"], ux, uy, rec["umask"])
                lp, ent = policy.logprob(ul, tl, ml, rec)
                ratio = torch.exp(lp - data["logp"][idx]); A = data["adv"][idx]
                pg = -torch.min(ratio * A, ratio.clamp(1 - a.clip, 1 + a.clip) * A).mean()
                vl = F.smooth_l1_loss(v, data["ret"][idx])
                with torch.no_grad():
                    bul, btl, bml, _ = bc.full(board, rec["G"], rec["uv"], ux, uy, rec["umask"])
                um = rec["umask"].float()
                def kl(pl, ql, m=None):
                    lp_, lq_ = F.log_softmax(pl, -1), F.log_softmax(ql, -1)
                    k_ = (lp_.exp() * (lp_ - lq_)).sum(-1)
                    return (k_ * m).sum() / m.sum().clamp(min=1) if m is not None else k_.mean()
                mm = lambda x: policy.market_mask(x, rec["hire_max"].long(), rec["land_max"].long())
                klv = kl(btl, tl, um) + kl(policy._masked(bul, rec["opm"]), policy._masked(ul, rec["opm"]), um) + kl(mm(bml), mm(ml))
                kl_coef = a.kl * max(0.0, 1 - it / max(1, a.iters))
                loss = pg + a.vf * vl - a.ent * ent["total"].mean() + kl_coef * klv
                opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step()
                if ep == 0 and s == 0: first_ratio = (ratio - 1).abs().mean().item()
                stats.append([pg.item(), vl.item(), ent["total"].mean().item(), klv.item(), (ratio - 1).abs().mean().item()])
        st_ = torch.tensor(stats).mean(0).tolist()
        rec = dict(iter=it, money_mean=final.mean().item(), money_p90=final.flatten().quantile(0.9).item(), money_max=final.max().item(),
                   pg=st_[0], vloss=st_[1], ent=st_[2], kl_bc=st_[3], ratio_dev=st_[4], ratio_first=first_ratio, secs_roll=round(t_roll), secs=round(time.time() - t0), samples=N)
        print(json.dumps(rec), flush=True); log.write(json.dumps(rec) + "\n"); log.flush()
        torch.save({"state": net.state_dict(), "gdim": ck["gdim"], "teams": teams, "iter": it}, f"{a.out}/last.pt")
        if it % 5 == 4: torch.save({"state": net.state_dict(), "gdim": ck["gdim"], "teams": teams, "iter": it}, f"{a.out}/it{it:03d}.pt")


if __name__ == "__main__":
    main()
