"""PPO fine-tuning over the exact batched gpuenv.

The rollout buffer is preallocated on the device: it avoids Python lists and a
large stack/concat peak.  Player zero is the trainable policy; player one is a
frozen/current league opponent.  Rewards are zero-sum changes in conservative
equity, with a terminal correction to the exact cash margin.
"""
import argparse
import json
import os
import sys
import time
from collections import Counter

import torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import policy
import gpufeat
from gpuenv import ops as O
from gpuenv import _consts as C
from gpuenv.env import VecKaggriculture

REC_KEYS = ("board", "G", "uv", "ux", "uy", "umask", "opm", "t", "o", "mb", "hire_max", "land_max", "minc")
STEPS = 719


def _new_net(ck, dev):
    """Build a policy from both old and F6 architecture-carrying checkpoints."""
    kw = {k: ck[k] for k in ("ch", "blocks") if k in ck}
    net = policy.PolicyNet(ck["gdim"], **kw).to(dev)
    net.load_state_dict(ck["state"], strict=False)
    return net


def _entropy_parts(value):
    """F1--F6 change entropy from a tensor to a dict; accept either revision."""
    if isinstance(value, dict):
        return value
    return {"total": value}


def _entropy_total(parts):
    # policy.logprob v2 exposes both the individual heads and their already
    # aggregated total.  Using every mapping value would count entropy twice.
    return parts["total"] if "total" in parts else sum(parts.values())


def _tensor_dtype(key, tensor):
    # Board dominates memory (T*B*30*10*10); fp16 has ample feature precision.
    if key == "board":
        return torch.float16
    return tensor.dtype


class StreamingBuffer:
    """Fixed [time, env, ...] device storage for a single trainable player."""
    def __init__(self, steps, batch):
        self.steps, self.batch, self.pos = steps, batch, 0
        self.data = {}

    def put(self, rec, logp, value, reward):
        if self.pos >= self.steps:
            raise RuntimeError("rollout buffer overflow")
        row = dict(rec)
        row.update(logp=logp, v=value, r=reward)
        if not self.data:
            for key, val in row.items():
                self.data[key] = torch.empty((self.steps, *val.shape), device=val.device,
                                             dtype=_tensor_dtype(key, val))
        for key, val in row.items():
            self.data[key][self.pos].copy_(val)
        self.pos += 1

    def terminal_add(self, correction):
        if self.pos != self.steps:
            raise RuntimeError("terminal correction before a complete rollout")
        self.data["r"][-1].add_(correction)

    def flat(self):
        if self.pos != self.steps:
            raise RuntimeError(f"incomplete rollout: {self.pos}/{self.steps}")
        return {k: v.reshape(self.steps * self.batch, *v.shape[2:]) for k, v in self.data.items()}


def conservative_equity(st):
    """Cash plus deliberately discounted immediately/liquidly usable assets.

    It is a training shaping signal, never a claim about official terminal
    money.  The last reward below corrects it exactly to the cash margin.
    """
    dev = st.money.device
    prices = st.market_price().float()                         # [B, 9]
    product = (st.shed[:, :, :O.N_PRODUCTS].float() +
               st.inv[:, :, :, :O.N_PRODUCTS].float().sum(2))
    # Selling an inventory moves the market curve and costs a market order;
    # value it below the displayed marginal price.
    assets = (product * prices[:, None, :] * 0.55).sum(-1)
    seed_cost = torch.tensor(C.CROP_SEED_COST, device=dev, dtype=torch.float32)
    animal_cost = torch.tensor(C.ANIMAL_COST, device=dev, dtype=torch.float32)
    assets = assets + (st.seeds.float() * seed_cost[None, None, :] * 0.45).sum(-1)
    animals_in_inv = st.inv[:, :, :, 9:12].float().sum(2)
    assets = assets + (animals_in_inv * animal_cost[None, None, :] * 0.45).sum(-1)
    # Mature crops have already produced an observable yield.  Their value is
    # discounted further because collection/pathing can still fail.
    day = int(st.step) // C.TURNS_PER_DAY
    crop_first = torch.tensor(C.CROP_FIRST_YIELD_DAY, device=dev)
    plant = st.kind == O.TILE_PLANT
    mature = plant & ((day - st.tday.long()) >= crop_first[st.species.long().clamp(0, 4)])
    crop_price = prices[:, None, None, :5].expand(-1, 2, st.kind.shape[-1], -1)
    crop_unit_price = crop_price.gather(-1, st.species.long().clamp(0, 4).unsqueeze(-1)).squeeze(-1)
    assets = assets + (mature.float() * st.tyield.float().clamp(min=0) * crop_unit_price * 0.20).sum(-1)
    return st.money.float() + assets


def _merge_actions(outputs, labels, names):
    """Select player-one action batch rows from named league policies."""
    chosen = None
    for idx, name in enumerate(names):
        action = outputs[name][0]
        mask = labels == idx
        if chosen is None:
            chosen = tuple(x.clone() for x in action)
        else:
            chosen = tuple(torch.where(mask.view(-1, *([1] * (x.ndim - 1))), x, old)
                           for old, x in zip(chosen, action))
    return chosen


def _league_labels(batch, dev, seed, names, probs):
    generator = torch.Generator(device=dev)
    generator.manual_seed(seed)
    p = torch.tensor(probs, dtype=torch.float32, device=dev)
    return torch.multinomial(p.expand(batch, -1), 1, generator=generator).squeeze(1)


def rollout(net, ve, batch, dev, team, seed_base, league, greedy=False):
    """Run player zero against a fixed per-environment league draw."""
    st = ve.reset(torch.arange(batch, device=dev) + seed_base)
    so = gpufeat.ShopOrder(batch, dev)
    names = list(league)
    probs = [league[n][1] for n in names]
    labels = _league_labels(batch, dev, seed_base ^ 0x9E3779B9, names, probs)
    buf = StreamingBuffer(STEPS, batch)
    eq_prev = conservative_equity(st)
    metric = {
        "unit_hist": torch.zeros(O.N_UNIT_OPS, dtype=torch.int64, device=dev),
        "market_hist": torch.zeros(O.N_MARKET_OPS, dtype=torch.int64, device=dev),
        "active_units": torch.zeros((), dtype=torch.int64, device=dev),
        "unit_noop": torch.zeros((), dtype=torch.int64, device=dev),
        "market_noop": torch.zeros((), dtype=torch.int64, device=dev),
        "league_counts": torch.bincount(labels, minlength=len(names)),
    }
    with torch.no_grad():
        for _ in range(STEPS):
            so.update(st)
            out0 = policy.act(net, st, 0, so, team, greedy=greedy)
            # Calling each opponent on the full batch keeps ShopOrder state
            # aligned and avoids host-side batch slicing in the hot loop.
            opponent_out = {name: policy.act(league[name][0], st, 1, so, league[name][2], greedy=False)
                            for name in names}
            out1 = _merge_actions(opponent_out, labels, names)
            st, _, _, _ = ve.step(st, policy.combine(out0[0], out1))
            eq = conservative_equity(st)
            reward = ((eq[:, 0] - eq[:, 1]) - (eq_prev[:, 0] - eq_prev[:, 1])) / 1e4
            eq_prev = eq
            _, logp, value, _, rec = out0
            buf.put(rec, logp, value, reward)
            farmer, hands, market = out0[0]
            unit_ops = torch.cat((farmer[:, None, 0], hands[..., 0]), 1).long()
            active = rec["umask"]
            metric["unit_hist"] += torch.bincount(unit_ops[active], minlength=O.N_UNIT_OPS)
            metric["active_units"] += active.sum()
            metric["unit_noop"] += (unit_ops[active] == O.OP_PASS).sum()
            market_ops = market[..., 0].long()
            metric["market_hist"] += torch.bincount(market_ops.flatten(), minlength=O.N_MARKET_OPS)
            metric["market_noop"] += (market_ops == O.MKT_NONE).sum()
    # Sum of equity deltas is end equity difference.  Correct terminally to
    # the true cash result required by the competition.
    cash_margin = st.money[:, 0].float() - st.money[:, 1].float()
    equity_margin = eq_prev[:, 0] - eq_prev[:, 1]
    buf.terminal_add((cash_margin - equity_margin) / 1e4)
    metric = {k: (v.detach().cpu() if torch.is_tensor(v) else v) for k, v in metric.items()}
    return buf, st.money.float(), metric, {name: int((labels == i).sum()) for i, name in enumerate(names)}


def gae(reward, value, gamma, lam):
    steps = reward.shape[0]
    adv = torch.zeros_like(reward)
    last = torch.zeros_like(reward[0])
    for t in reversed(range(steps)):
        next_value = value[t + 1] if t + 1 < steps else torch.zeros_like(value[t])
        delta = reward[t] + gamma * next_value - value[t]
        last = delta + gamma * lam * last
        adv[t] = last
    return adv, adv + value


def _explained_variance(pred, target):
    var_y = torch.var(target)
    if var_y <= 1e-12:
        return torch.tensor(0.0, device=target.device)
    return 1.0 - torch.var(target - pred) / var_y


def _team_vec(ck, team, dev):
    teams = ck.get("teams", ["mmpq", "dsm", "mgoose"]); v = torch.zeros((1, len(teams)), device=dev)
    v[0, teams.index(team) if team in teams else 0] = 1
    return v


def _league_from_args(a, ck, net, bc, dev):
    """Return name -> (net, probability, team_vec). --league-snapshot/--league-double accept CKPT or CKPT:TEAM
    (TEAM = the team the opponent imitates; defaults to the learner's team)."""
    def load(spec):
        path, _, team = spec.partition(":")
        oc = torch.load(path, map_location=dev)
        return _new_net(oc, dev).eval(), _team_vec(oc, team or a.team, dev)
    snapshots = [load(s_) for s_ in a.league_snapshot]
    doubles = [load(s_) for s_ in a.league_double]
    own = _team_vec(ck, a.team, dev)
    if not snapshots and not doubles:
        return {"current": (net, 1.0, own)}
    entries = [("current", net, .30, own)]
    for i, (m, tv) in enumerate(snapshots):
        entries.append((f"snapshot{i}", m, .35 / len(snapshots), tv))
    for i, (m, tv) in enumerate(doubles):
        entries.append((f"double{i}", m, .25 / len(doubles), tv))
    entries.append(("bc_fallback", bc, .10, own))
    total = sum(x[2] for x in entries)
    return {name: (model, weight / total, tv) for name, model, weight, tv in entries}


def _restore_resume(path, net, opt, dev):
    ck = torch.load(path, map_location=dev)
    net.load_state_dict(ck["state"])
    if "optimizer" in ck:
        opt.load_state_dict(ck["optimizer"])
    if "rng_cpu" in ck:
        torch.set_rng_state(ck["rng_cpu"].cpu())
    if dev.startswith("cuda") and "rng_cuda" in ck:
        torch.cuda.set_rng_state_all([x.cpu() for x in ck["rng_cuda"]])
    return int(ck["iter"]) + 1


def _save(path, net, opt, source_ck, teams, iteration):
    payload = {
        "state": net.state_dict(), "gdim": source_ck["gdim"], "teams": teams, "iter": iteration,
        "optimizer": opt.state_dict(), "rng_cpu": torch.get_rng_state(),
        "ch": source_ck.get("ch", 96), "blocks": source_ck.get("blocks", 6),
    }
    if torch.cuda.is_available():
        payload["rng_cuda"] = torch.cuda.get_rng_state_all()
    torch.save(payload, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--envs", type=int, default=256)
    ap.add_argument("--iters", type=int, default=50)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--mb", type=int, default=8192)
    ap.add_argument("--gamma", type=float, default=1.0)
    ap.add_argument("--lam", type=float, default=.995)
    ap.add_argument("--clip", type=float, default=.2)
    ap.add_argument("--ent", type=float, default=.001)
    ap.add_argument("--kl", type=float, default=.05); ap.add_argument("--stop-at", type=int, default=0, help="stop after this iteration index (rounds keep one KL horizon = --iters)"); ap.add_argument("--kl-floor", type=float, default=0.0, help="minimum KL-to-BC coefficient (style preservation for team doubles)")
    ap.add_argument("--team", default="dsm")
    ap.add_argument("--vf", type=float, default=.5)
    ap.add_argument("--value-warmup", type=int, default=0, help="value-only iterations before policy updates")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--amp", default="none", choices=["none", "bf16"])
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--league-snapshot", action="append", default=[], metavar="CKPT")
    ap.add_argument("--league-double", action="append", default=[], metavar="CKPT")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if not 0 < a.gamma <= 1 or not 0 <= a.lam <= 1:
        ap.error("gamma must be in (0,1] and lambda in [0,1]")
    dev = a.device
    torch.manual_seed(a.seed)
    if a.amp == "bf16":
        policy.AMP = torch.bfloat16
    source_ck = torch.load(a.init, map_location=dev)
    net = _new_net(source_ck, dev)
    bc = _new_net(source_ck, dev).eval()
    for parameter in bc.parameters():
        parameter.requires_grad_(False)
    teams = source_ck.get("teams", ["mmpq", "dsm", "mgoose"])
    if a.team not in teams:
        ap.error(f"team {a.team!r} absent from checkpoint teams={teams}")
    team = torch.zeros((1, len(teams)), device=dev)
    team[0, teams.index(a.team)] = 1
    opt = torch.optim.Adam(net.parameters(), lr=a.lr)
    start = 0
    last = f"{a.out}/last.pt"
    if a.resume and os.path.exists(last):
        start = _restore_resume(last, net, opt, dev)
        print("resumed at iter", start, flush=True)
    league = _league_from_args(a, source_ck, net, bc, dev)
    ve = VecKaggriculture(a.envs, device=dev)
    with open(f"{a.out}/args.json", "w") as fh:
        json.dump({**vars(a), "league_effective": {k: v[1] for k, v in league.items()}}, fh, indent=1)
    log = open(f"{a.out}/log.jsonl", "a")
    for it in range(start, min(a.iters, a.stop_at) if a.stop_at else a.iters):
        t0 = time.time()
        net.eval()
        buf, final, action_metric, league_counts = rollout(
            net, ve, a.envs, dev, team, seed_base=1_000_003 * (it + 1) + 7_919 * a.seed,
            league=league,
        )
        roll_seconds = time.time() - t0
        flat = buf.flat()
        reward = buf.data["r"]
        values = buf.data["v"]
        adv, ret = gae(reward, values, a.gamma, a.lam)
        data = {k: flat[k] for k in REC_KEYS + ("logp",)}
        data["adv"] = adv.reshape(-1)
        data["ret"] = ret.reshape(-1)
        data["v"] = values.reshape(-1)
        data["adv"] = (data["adv"] - data["adv"].mean()) / (data["adv"].std() + 1e-8)
        del buf
        samples = data["adv"].numel()
        stats = Counter()
        n_updates = 0
        net.train()
        value_only = it < a.value_warmup
        for epoch in range(a.epochs):
            permutation = torch.randperm(samples, device=dev)
            for offset in range(0, samples, a.mb):
                idx = permutation[offset:offset + a.mb]
                rec = {k: data[k][idx] for k in REC_KEYS}
                board = rec["board"].float()
                ul, tl, ml, value = net.full(board, rec["G"], rec["uv"], rec["ux"].long(), rec["uy"].long(), rec["umask"])
                logp, raw_entropy = policy.logprob(ul, tl, ml, rec)
                entropy = _entropy_parts(raw_entropy)
                ent_total = _entropy_total(entropy)
                log_ratio = logp - data["logp"][idx]
                ratio = torch.exp(log_ratio)
                advantage = data["adv"][idx]
                policy_loss = -torch.min(ratio * advantage, ratio.clamp(1 - a.clip, 1 + a.clip) * advantage).mean()
                value_loss = F.smooth_l1_loss(value, data["ret"][idx])
                with torch.no_grad():
                    bul, btl, bml, _ = bc.full(board, rec["G"], rec["uv"], rec["ux"].long(), rec["uy"].long(), rec["umask"])
                unit_mask = rec["umask"].float()
                def kl(p_logits, q_logits, mask=None):
                    lp, lq = F.log_softmax(p_logits, -1), F.log_softmax(q_logits, -1)
                    val = (lp.exp() * (lp - lq)).sum(-1)
                    return (val * mask).sum() / mask.sum().clamp(min=1) if mask is not None else val.mean()
                mm = lambda x: policy.market_mask(x, rec["hire_max"].long(), rec["land_max"].long())
                kl_bc = (kl(btl, tl, unit_mask) +
                         kl(policy._masked(bul, rec["opm"]), policy._masked(ul, rec["opm"]), unit_mask) + kl(mm(bml), mm(ml)))
                kl_coef = max(a.kl_floor, a.kl * max(0.0, 1 - it / max(1, a.iters)))
                loss = a.vf * value_loss if value_only else policy_loss + a.vf * value_loss - a.ent * ent_total.mean() + kl_coef * kl_bc
                opt.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
                opt.step()
                with torch.no_grad():
                    stats["pg"] += float(policy_loss)
                    stats["vloss"] += float(value_loss)
                    stats["kl_bc"] += float(kl_bc)
                    stats["approx_kl"] += float((data["logp"][idx] - logp).mean())
                    stats["clipfrac"] += float(((ratio - 1).abs() > a.clip).float().mean())
                    for key, val in entropy.items():
                        stats[f"entropy_{key}"] += float(val.mean())
                n_updates += 1
        unit_hist = action_metric["unit_hist"].tolist()
        market_hist = action_metric["market_hist"].tolist()
        active_units = max(1, int(action_metric["active_units"]))
        market_slots = max(1, a.envs * STEPS * O.MAX_ORDERS)
        record = {
            "iter": it,
            "money_mean": final.mean().item(),
            "money_p90": final.flatten().quantile(.9).item(),
            "money_max": final.max().item(),
            "equity_reward_mean": reward.mean().item(),
            "explained_variance": _explained_variance(data["v"], data["ret"]).item(),
            "value_only": value_only,
            "secs_roll": round(roll_seconds),
            "secs": round(time.time() - t0),
            "samples": samples,
            "league_envs": league_counts,
            "unit_op_distribution": [x / active_units for x in unit_hist],
            "market_op_distribution": [x / market_slots for x in market_hist],
            "unit_noop_fraction": int(action_metric["unit_noop"]) / active_units,
            "market_noop_fraction": int(action_metric["market_noop"]) / market_slots,
            # The gpuenv currently exposes no per-action rejection bit.  F11
            # will add it; until then this is explicitly an honest placeholder.
            "rejected_actions": None,
        }
        record.update({key: value / max(1, n_updates) for key, value in stats.items()})
        print(json.dumps(record), flush=True)
        log.write(json.dumps(record) + "\n")
        log.flush()
        _save(last, net, opt, source_ck, teams, it)
        if it % 5 == 4:
            _save(f"{a.out}/it{it:03d}.pt", net, opt, source_ck, teams, it)


if __name__ == "__main__":
    main()
