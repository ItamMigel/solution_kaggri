"""Batched policy on gpuenv State: BC network (+ value head) -> sampled gpuenv Actions, log-probs, entropy.
Factorisation per unit: target cell t ~ Cat(target logits | unlocked);
  if t == unit cell: op ~ Cat(op logits | legal, non-move)      logp = log p(t) + log p(op)
  else: deterministic greedy step toward t (best-scored legal move); if no legal move: op ~ Cat(op | legal)
Market: per key bucket ~ Cat(market logits); orders built in fixed order, then sequential affordability filter.
Everything needed to recompute log-probs is returned in `rec` (inputs + masks + choices)."""
import os, sys
import torch, torch.nn as nn, torch.nn.functional as F
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "bc")); sys.path.insert(0, os.path.join(HERE, ".."))
import feat, gpufeat, train as bctrain
from gpuenv import ops as O
from gpuenv._state import Actions

NOP = len(feat.UNIT_OPS); NK = len(feat.MKT_KEYS); NB = feat.MKT_MAX + 1
IDX = feat.UNIT_IDX
MOVE_IDS = [IDX[k] for k in ("NORTH", "SOUTH", "EAST", "WEST")]
DXY = {IDX["NORTH"]: (0, -1), IDX["SOUTH"]: (0, 1), IDX["EAST"]: (1, 0), IDX["WEST"]: (-1, 0)}

# feat.UNIT_OPS -> gpuenv (op, arg1)
def _op_table():
    op = torch.zeros(NOP, dtype=torch.long); a1 = torch.zeros(NOP, dtype=torch.long)
    for i, k in enumerate(feat.UNIT_OPS):
        name, _, it = k.partition(":")
        op[i] = O.UNIT_OP_ID[name]
        if it: a1[i] = O.ITEM_ID[it]
    return op, a1
OPT, ARG1 = _op_table()
SEED_COST = torch.tensor([10, 20, 50, 100, 80]); ANIMAL_COST = torch.tensor([300, 400, 500]); LAND_COST = torch.tensor([1000, 2000, 4000, 10**12])
FIB = torch.tensor([1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765, 10946], dtype=torch.long)
# market key -> gpuenv (op, item); order of emission
def _mkt_table():
    op = torch.zeros(NK, dtype=torch.long); it = torch.zeros(NK, dtype=torch.long)
    for i, k in enumerate(feat.MKT_KEYS):
        name, _, item = k.partition(":")
        op[i] = O.MARKET_OP_ID[name]; it[i] = O.ITEM_ID[item] if item else 0
    order = torch.tensor([feat.MKT_IDX[k] for k in feat.MKT_ORDER])
    return op, it, order
MOP, MIT, MORDER = _mkt_table()


AMP = None  # set to torch.bfloat16 on H100/A100 for the conv trunk; heads stay fp32


class PolicyNet(bctrain.Net):
    def __init__(self, gdim, ch=96, blocks=6):
        super().__init__(gdim, ch, blocks)
        self.value = nn.Sequential(nn.Linear(2 * ch + gdim, 256), nn.ReLU(), nn.Linear(256, 1))

    def full(self, B, G, uv, ux, uy, umask):
        """B[N,C,10,10] G[N,g] uv[N,U,d] ux/uy[N,U] -> unit op logits [N,U,NOP], target logits [N,U,100], market [N,NK,NB], value [N]"""
        if AMP is not None and B.is_cuda:
            with torch.autocast("cuda", dtype=AMP):
                h = self.trunk(B, G)
            h = h.float()
        else:
            h = self.trunk(B, G)
        N_, C = h.shape[:2]; U = ux.shape[1]
        hu = h.flatten(2).gather(2, (uy * 10 + ux)[:, None, :].expand(N_, C, U)).transpose(1, 2)  # [N,U,C]
        uin = torch.cat([hu, uv, G[:, None, :].expand(N_, U, G.shape[1])], -1)
        ul = self.unit(uin)
        tl = torch.einsum("nuc,ncp->nup", self.tq(uin), h.flatten(2)) / (C ** 0.5)
        pooled = torch.cat([h.mean((2, 3)), h.amax((2, 3)), G], 1)
        ml = self.mkt(pooled).view(-1, NK, NB)
        return ul, tl, ml, self.value(pooled).squeeze(-1)


STRUCT_OF_ANIMAL = torch.tensor([O.TILE_COOP, O.TILE_PASTURE, O.TILE_PASTURE])  # goose, cow, sheep


def tile_masks(st, p, ux, uy, umask):
    """Static (pre-allocation) per-unit legality following kaggriculture.py _apply_unit_action exactly.
    Returns base [B,U,NOP] (excluding PLANT/PICKUP, which depend on running seeds/shed) and helper tensors."""
    dev = ux.device; B, U = ux.shape
    kind = st.kind[:, p].long(); cell = uy * 10 + ux
    g = lambda t: t.gather(1, cell)
    tk = g(kind); sp = g(st.species[:, p].long()); flag = g(st.tflag[:, p]); yld = g(st.tyield[:, p].long())
    cared = g(st.tcared[:, p]); favail = g(st.tfavail[:, p]); age = int(st.step) // 24 - g(st.tday[:, p].long())
    inv = st.inv[:, p].long()
    m = torch.zeros((B, U, NOP), dtype=torch.bool, device=dev)
    for mid, (dx, dy) in DXY.items():
        nx = ux + dx; ny = uy + dy
        m[..., mid] = (nx >= 0) & (nx < 10) & (ny >= 0) & (ny < 10)          # LOCKED tiles are walkable
    locked = tk == O.TILE_LOCKED
    plant = tk == O.TILE_PLANT; animal = tk == O.TILE_ANIMAL; empty = tk == O.TILE_EMPTY
    first_yield = gpufeat.FIRST_YIELD.to(dev)[sp.clamp(0, 4)]
    m[..., IDX["WATER"]] = plant & ~flag
    m[..., IDX["HARVEST"]] = ((plant & (age >= first_yield)) | animal) & (yld > 0)
    m[..., IDX["FERTILIZE"]] = plant & (inv[..., O.ITEM_FERTILIZER] > 0)
    m[..., IDX["FEED"]] = animal & ~flag & (inv[..., O.ITEM_WHEAT] > 0)
    m[..., IDX["CARE"]] = animal & ~cared
    m[..., IDX["COLLECT_FERTILIZER"]] = animal & favail
    m[..., IDX["BUILD_COOP"]] = empty; m[..., IDX["BUILD_PASTURE"]] = empty
    m[..., IDX["DIG"]] = ~empty & ~locked & ~animal
    adj = gpufeat.SHED_ADJ_MASK.to(dev)[cell]
    m[..., IDX["DROP"]] = adj & (inv.sum(-1) > 0)
    for it, name in enumerate(feat.ITEMS):
        has = inv[..., it] > 0
        if it >= 9:
            on_struct = (tk == int(STRUCT_OF_ANIMAL[it - 9]))
            m[..., IDX["PLACE:" + name]] = has & (on_struct | adj)
        else:
            m[..., IDX["PLACE:" + name]] = has & adj
    m[..., IDX["PASS"]] = True
    m &= umask[..., None]; m[..., IDX["PASS"]] = True
    return m, dict(empty=empty & ~locked, adj=adj)


PLANT_IDS = [IDX["PLANT:" + c] for c in feat.CROPS]
PICK_IDS = [IDX["PICKUP:" + i] for i in feat.ITEMS]
MOVE_T = torch.tensor(MOVE_IDS)
PLANT_T = torch.tensor(PLANT_IDS)
PICK_T = torch.tensor(PICK_IDS)


def act(net, st, p, so, team_vec, greedy=False):
    board, G, uv, ux, uy, umask = gpufeat.features(st, p, so)
    G = torch.cat([G, team_vec.expand(G.shape[0], -1)], 1)
    ul, tl, ml, v = net.full(board, G, uv, ux, uy, umask)
    B, U = ux.shape; dev = ux.device
    base, aux = tile_masks(st, p, ux, uy, umask)
    # targets: any cell (LOCKED shed-access tiles are legitimate destinations)
    t = tl.argmax(-1) if greedy else torch.distributions.Categorical(logits=tl).sample()
    cur = uy.long() * 10 + ux.long(); tx = t % 10; ty = t // 10
    want = torch.zeros((B, U, NOP), dtype=torch.bool, device=dev)
    want[..., IDX["EAST"]] = tx > ux; want[..., IDX["WEST"]] = tx < ux; want[..., IDX["SOUTH"]] = ty > uy; want[..., IDX["NORTH"]] = ty < uy
    seeds_left = st.seeds[:, p].long().clone(); shed_left = st.shed[:, p].long().clone()
    used = torch.zeros((B, U, NOP), dtype=torch.bool, device=dev); o = torch.zeros((B, U), dtype=torch.long, device=dev)
    qty = torch.zeros((B, U), dtype=torch.long, device=dev)
    U_eff = int(umask.any(0).sum())  # slots beyond the largest hand count in the batch are PASS
    plant_ids = PLANT_T.to(dev); pick_ids = PICK_T.to(dev)
    for u in range(U_eff):
        mu = base[:, u].clone()
        um = umask[:, u:u + 1]
        mu[:, plant_ids] = aux["empty"][:, u:u + 1] & (seeds_left > 0) & um          # PLANT c needs empty tile + seeds left
        mu[:, pick_ids] = aux["adj"][:, u:u + 1] & (shed_left > 0) & um              # PICKUP i needs shed-adjacent + stock left
        mv = want[:, u] & mu
        off = (t[:, u] != cur[:, u]) & mv.any(-1)
        nonmove = mu.clone(); nonmove[:, MOVE_T.to(dev)] = False
        mask = torch.where(off[:, None], mv, nonmove)
        lg = ul[:, u].masked_fill(~mask, -1e9)
        ou = lg.argmax(-1) if greedy else torch.distributions.Categorical(logits=lg).sample()
        used[:, u] = mask; o[:, u] = ou
        seeds_left -= (ou[:, None] == plant_ids[None, :]).long()
        it_ = ARG1.to(dev)[ou].clamp(0, 11); is_pick = OPT.to(dev)[ou] == O.OP_PICKUP
        n = torch.where(it_ >= 9, torch.ones_like(it_), torch.where(it_ == O.ITEM_FERTILIZER, 4, 3))
        n = torch.minimum(n, shed_left.gather(1, it_[:, None]).squeeze(1)).clamp(min=1)
        qty[:, u] = torch.where(is_pick, n, 0)
        shed_left.scatter_add_(1, it_[:, None], -(n * is_pick.long())[:, None])
    # market (P0/P1 fix): sequential over keys in emission order; each key's bucket is capped by the remaining order slots
    # (and hire/land limits) BEFORE sampling, so the recorded bucket is exactly what the engine receives.
    hire_max = (O.MAX_HANDS - st.n_hands[:, p].long()).clamp(min=0, max=feat.MKT_MAX)
    land_max = (3 - st.land[:, p].long()).clamp(min=0)
    mb, mcap = sample_market(ml, hire_max, land_max, greedy)
    orders = build_market(mb)
    rec = dict(board=board, G=G, uv=uv, ux=ux.to(torch.int8), uy=uy.to(torch.int8), umask=umask, opm=used,
               t=t.to(torch.int8), o=o.to(torch.int8), mb=mb.to(torch.int8), mcap=mcap.to(torch.int8))
    logp, ent = logprob(ul, tl, ml, rec)
    farmer, hands = unit_triples(o, qty, st, p, umask)
    return (farmer, hands, orders), logp, v, ent, rec


def _masked(logits, mask):
    return logits.masked_fill(~mask, -1e9)


MKT_REP = torch.tensor([k.split(":")[0] in ("HIRE", "BUY_LAND", "BUY_ANIMAL") for k in feat.MKT_KEYS])


def market_mask(ml, mcap):
    """Mask market bucket logits above each key's cap: ml [N,NK,NB], mcap [N,NK] int."""
    b = torch.arange(NB, device=ml.device)
    return ml.masked_fill(b[None, None, :] > mcap.long()[..., None], -1e9)


def sample_market(ml, hire_max, land_max, greedy):
    """Sequential capped sampling in emission order (MKT_ORDER). Returns buckets [B,NK] and caps [B,NK]."""
    B = ml.shape[0]; dev = ml.device
    remaining = torch.full((B,), O.MAX_ORDERS, dtype=torch.long, device=dev)
    mb = torch.zeros((B, NK), dtype=torch.long, device=dev); mcap = torch.zeros((B, NK), dtype=torch.long, device=dev)
    rep = MKT_REP.to(dev)
    for k in MORDER.tolist():
        key = feat.MKT_KEYS[k]
        if rep[k]:
            cap = remaining.clamp(max=feat.MKT_MAX)
            if key == "HIRE": cap = torch.minimum(cap, hire_max)
            if key == "BUY_LAND": cap = torch.minimum(cap, land_max)
        else:
            cap = torch.where(remaining > 0, torch.full_like(remaining, feat.MKT_MAX), torch.zeros_like(remaining))
        lg = market_mask(ml[:, k:k + 1], cap[:, None])[:, 0]
        q = lg.argmax(-1) if greedy else torch.distributions.Categorical(logits=lg).sample()
        mb[:, k] = q; mcap[:, k] = cap
        remaining = remaining - torch.where(rep[k], q, (q > 0).long())
    return mb, mcap


def logprob(ul, tl, ml, rec):
    """Recompute log-prob / entropies of recorded choices. Unit: log p(target) + log p(op | recorded mask).
    Market: sum over keys that were decision-relevant (bucket 0 or actually emitted; truncated keys excluded)."""
    umask = rec["umask"]; t = rec["t"].long() % 100; o = rec["o"].long() % NOP
    tlp = F.log_softmax(tl, -1); lp_t = tlp.gather(-1, t[..., None]).squeeze(-1)
    olp = F.log_softmax(ul.masked_fill(~rec["opm"], -1e9), -1); lp_o = olp.gather(-1, o[..., None]).squeeze(-1)
    unit_lp = ((lp_t + lp_o) * umask).sum(-1)
    mlp = F.log_softmax(market_mask(ml, rec["mcap"]), -1)
    lp_m = mlp.gather(-1, rec["mb"].long()[..., None]).squeeze(-1).sum(-1)
    ent_t = (-(tlp.exp() * tlp).sum(-1) * umask).sum(-1)
    ent_o = (-(olp.exp() * olp.clamp(min=-30)).sum(-1) * umask).sum(-1)
    ent_m = -(mlp.exp() * mlp.clamp(min=-30)).sum(-1).sum(-1)
    return unit_lp + lp_m, dict(target=ent_t, op=ent_o, market=ent_m, total=ent_t + ent_o + ent_m)


def unit_triples(o, qty, st, p, umask):
    dev = o.device
    opt = OPT.to(dev)[o]; a1 = ARG1.to(dev)[o]; item = a1.clamp(0, 11)
    inv = st.inv[:, p].long()
    is_place = opt == O.OP_PLACE; animal = item >= 9
    place_n = torch.where(animal | (item == O.ITEM_FERTILIZER), torch.ones_like(item), inv.gather(2, item[..., None]).squeeze(-1)).clamp(min=1)
    a2 = torch.where(opt == O.OP_PICKUP, qty, torch.where(is_place, place_n, torch.zeros_like(item)))
    opt = torch.where(umask, opt, torch.zeros_like(opt))
    trip = torch.stack([opt, a1, a2], -1)
    return trip[:, 0], trip[:, 1:]


def build_market(mb):
    """Fixed key order; HIRE/LAND/ANIMAL one unit per order; others one order with qty. Caps guarantee <= MAX_ORDERS."""
    dev = mb.device; B = mb.shape[0]; q = mb.long()
    R = O.MAX_ORDERS; mop = MOP.to(dev); mit = MIT.to(dev); order = MORDER.to(dev)
    kop = mop[order]; kit = mit[order]; K = len(order)
    rep_key = (kop == O.MKT_HIRE) | (kop == O.MKT_BUY_LAND) | (kop == O.MKT_BUY_ANIMAL)
    qo = q[:, order]; r = torch.arange(R, device=dev)
    want = torch.where(rep_key[None, :, None], qo[..., None] > r, (qo[..., None] > 0) & (r == 0))
    qty = torch.where(rep_key[None, :, None], torch.ones_like(qo)[..., None].expand(-1, -1, R), qo[..., None].expand(-1, -1, R))
    wf = want.reshape(B, -1); rank = torch.cumsum(wf.long(), 1) - 1; ok = wf & (rank < O.MAX_ORDERS)
    val = torch.stack([kop[:, None].expand(-1, R).reshape(1, -1).expand(B, -1), kit[:, None].expand(-1, R).reshape(1, -1).expand(B, -1), qty.reshape(B, -1)], -1)
    dst = torch.where(ok, rank, torch.full_like(rank, O.MAX_ORDERS))
    buf = torch.zeros((B, O.MAX_ORDERS + 1, 3), dtype=torch.long, device=dev)
    buf.scatter_(1, dst[..., None].expand(-1, -1, 3), val * ok[..., None])
    return buf[:, :O.MAX_ORDERS]


def combine(a0, a1):
    """two players' (farmer, hands, market) -> gpuenv Actions."""
    f = torch.stack([a0[0], a1[0]], 1).to(torch.int16); h = torch.stack([a0[1], a1[1]], 1).to(torch.int16); m = torch.stack([a0[2], a1[2]], 1).to(torch.int16)
    return Actions(f, h, m)
