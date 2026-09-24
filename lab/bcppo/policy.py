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


def legal_masks(st, p, ux, uy, umask):
    """op mask [B,U,NOP] (moves included) and target mask [B,100] (unlocked cells)."""
    dev = ux.device; B, U = ux.shape
    kind = st.kind[:, p].long(); cell = uy * 10 + ux
    tk = kind.gather(1, cell)
    inv = st.inv[:, p].long(); shed = st.shed[:, p].long(); seeds = st.seeds[:, p].long()
    m = torch.ones((B, U, NOP), dtype=torch.bool, device=dev)
    for mid, (dx, dy) in DXY.items():
        nx = ux + dx; ny = uy + dy; inb = (nx >= 0) & (nx < 10) & (ny >= 0) & (ny < 10)
        nk = kind.gather(1, (ny.clamp(0, 9) * 10 + nx.clamp(0, 9)))
        m[..., mid] = inb & (nk != O.TILE_LOCKED)
    plant = tk == O.TILE_PLANT; animal = tk == O.TILE_ANIMAL; empty = tk == O.TILE_EMPTY
    for k in ("WATER", "HARVEST"): m[..., IDX[k]] = plant
    m[..., IDX["FERTILIZE"]] = plant & (inv[..., O.ITEM_FERTILIZER] > 0)
    for k in ("CARE", "COLLECT_FERTILIZER"): m[..., IDX[k]] = animal
    m[..., IDX["FEED"]] = animal & (inv[..., O.ITEM_WHEAT] > 0)
    for c, name in enumerate(feat.CROPS): m[..., IDX["PLANT:" + name]] = empty & (seeds[:, None, c] > 0)
    m[..., IDX["BUILD_COOP"]] = empty; m[..., IDX["BUILD_PASTURE"]] = empty
    m[..., IDX["DIG"]] = (tk == O.TILE_WEED) | plant
    adj = gpufeat.SHED_ADJ_MASK.to(dev)[cell]
    m[..., IDX["DROP"]] = adj & (inv.sum(-1) > 0)
    for it, name in enumerate(feat.ITEMS):
        m[..., IDX["PICKUP:" + name]] = adj & (shed[:, None, it] > 0)
        m[..., IDX["PLACE:" + name]] = inv[..., it] > 0
    m &= umask[..., None]
    m[..., IDX["PASS"]] = True
    tmask = kind != O.TILE_LOCKED
    return m, tmask


def act(net, st, p, so, team_vec, greedy=False):
    board, G, uv, ux, uy, umask = gpufeat.features(st, p, so)
    G = torch.cat([G, team_vec.expand(G.shape[0], -1)], 1)
    opm, tm = legal_masks(st, p, ux, uy, umask)
    ul, tl, ml, v = net.full(board, G, uv, ux, uy, umask)
    rec = dict(board=board, G=G, uv=uv, ux=ux.to(torch.int8), uy=uy.to(torch.int8), umask=umask, opm=opm, tm=tm)
    t_choice, o_choice, at_t, need_op, mkt_b = sample(ul, tl, ml, opm, tm, ux, uy, greedy)
    rec.update(t=t_choice.to(torch.int8), o=o_choice.to(torch.int8), need_op=need_op, mb=mkt_b.to(torch.int8))
    logp, ent = logprob(ul, tl, ml, rec)
    actions = build_actions(st, p, o_choice, umask, mkt_b)
    return actions, logp, v, ent, rec


def _masked(logits, mask):
    return logits.masked_fill(~mask, -1e9)


def sample(ul, tl, ml, opm, tm, ux, uy, greedy):
    B, U = ux.shape
    tlm = _masked(tl, tm[:, None, :])
    t = tlm.argmax(-1) if greedy else torch.distributions.Categorical(logits=tlm).sample()
    cur = uy.long() * 10 + ux.long(); at_t = t == cur
    tx = t % 10; ty = t // 10
    # greedy move toward target among legal moves, scored by op logits
    want = torch.zeros_like(opm)
    want[..., IDX["EAST"]] = tx > ux; want[..., IDX["WEST"]] = tx < ux; want[..., IDX["SOUTH"]] = ty > uy; want[..., IDX["NORTH"]] = ty < uy
    mv_ok = want & opm
    has_move = mv_ok.any(-1) & ~at_t
    mv = _masked(ul, mv_ok).argmax(-1)
    nonmove = opm.clone(); nonmove[..., MOVE_IDS] = False
    need_op = ~has_move
    op_mask = torch.where(at_t[..., None], nonmove, opm)  # at target: work ops; stuck: anything legal
    olm = _masked(ul, op_mask)
    o = olm.argmax(-1) if greedy else torch.distributions.Categorical(logits=olm).sample()
    o = torch.where(has_move, mv, o)
    mb = ml.argmax(-1) if greedy else torch.distributions.Categorical(logits=ml).sample()
    return t, o, at_t, need_op, mb


def logprob(ul, tl, ml, rec):
    """Recompute log-prob and entropy of recorded choices under current logits."""
    ux = rec["ux"].long(); uy = rec["uy"].long(); umask = rec["umask"]; opm = rec["opm"]; tm = rec["tm"]
    t = rec["t"].long() % 100; o = rec["o"].long(); need_op = rec["need_op"]
    tlp = F.log_softmax(_masked(tl, tm[:, None, :]), -1)
    lp_t = tlp.gather(-1, t[..., None]).squeeze(-1)
    cur = uy * 10 + ux; at_t = t == cur
    nonmove = opm.clone(); nonmove[..., MOVE_IDS] = False
    op_mask = torch.where(at_t[..., None], nonmove, opm)
    olp = F.log_softmax(_masked(ul, op_mask), -1)
    lp_o = olp.gather(-1, o[..., None]).squeeze(-1)
    unit_lp = (lp_t + torch.where(need_op, lp_o, torch.zeros_like(lp_o))) * umask
    mlp = F.log_softmax(ml, -1); lp_m = mlp.gather(-1, rec["mb"].long()[..., None]).squeeze(-1).sum(-1)
    ent_t = -(tlp.exp() * tlp.clamp(min=-30)).sum(-1); ent_m = -(mlp.exp() * mlp.clamp(min=-30)).sum((-1, -2))
    ent = (ent_t * umask).sum(-1) + ent_m
    return unit_lp.sum(-1) + lp_m, ent


def build_actions(st, p, o, umask, mb):
    """-> gpuenv Actions for player p only: farmer [B,3], hands [B,MAX_HANDS,3], market [B,MAX_ORDERS,3]."""
    dev = o.device; B, U = o.shape
    opt = OPT.to(dev)[o]; a1 = ARG1.to(dev)[o]
    shed = st.shed[:, p].long(); inv = st.inv[:, p].long()
    item = a1.clamp(0, 11)
    is_pick = opt == O.OP_PICKUP; is_place = opt == O.OP_PLACE
    animal = item >= 9
    pick_n = torch.where(animal, torch.ones_like(item), torch.where(item == O.ITEM_FERTILIZER, 4, 3))
    pick_n = torch.minimum(pick_n, shed.gather(1, item)).clamp(min=1)
    place_n = torch.where(animal | (item == O.ITEM_FERTILIZER), torch.ones_like(item), inv.gather(2, item[..., None]).squeeze(-1)).clamp(min=1)
    a2 = torch.where(is_pick, pick_n, torch.where(is_place, place_n, torch.zeros_like(item)))
    opt = torch.where(umask, opt, torch.zeros_like(opt))
    trip = torch.stack([opt, a1, a2], -1)
    farmer = trip[:, 0]; hands = trip[:, 1:]
    # market
    q = mb.long()  # [B,NK] quantity per key
    orders = torch.zeros((B, O.MAX_ORDERS, 3), dtype=torch.long, device=dev); n = torch.zeros(B, dtype=torch.long, device=dev)
    money = st.money[:, p].long().clone(); hires = st.hires_today[:, p].long().clone(); land = st.land[:, p].long().clone()
    prices = st.market_price()[:, :].long()
    mop = MOP.to(dev); mit = MIT.to(dev)
    # expand every key into up to R single slots (HIRE/LAND/ANIMAL: one unit per order; others: one order with qty).
    # Prefix-affordability rule (vectorised, no host syncs): slots in fixed order, accept slot j iff wanted and the
    # cumulative cost of all wanted slots up to j fits the money; keep at most MAX_ORDERS accepted.
    R = O.MAX_ORDERS
    mop = MOP.to(dev); mit = MIT.to(dev); order = MORDER.to(dev)
    kop = mop[order]; kit = mit[order]; K = len(order)
    rep_key = (kop == O.MKT_HIRE) | (kop == O.MKT_BUY_LAND) | (kop == O.MKT_BUY_ANIMAL)
    qo = q[:, order]; r = torch.arange(R, device=dev)
    want = torch.where(rep_key[None, :, None], qo[..., None] > r, (qo[..., None] > 0) & (r == 0))            # [B,K,R]
    qty = torch.where(rep_key[None, :, None], torch.ones_like(qo)[..., None].expand(-1, -1, R), qo[..., None].expand(-1, -1, R))
    hires0 = st.hires_today[:, p].long(); land0 = st.land[:, p].long(); money = st.money[:, p].long()
    prices = st.market_price().long()                                                                          # [B,9]
    itc = kit.clamp(0, 11)
    unit_cost = torch.zeros((B, K), dtype=torch.long, device=dev)
    unit_cost = torch.where((kop == O.MKT_BUY_SEED)[None], SEED_COST.to(dev)[itc.clamp(max=4)][None].expand(B, -1), unit_cost)
    unit_cost = torch.where((kop == O.MKT_BUY_ANIMAL)[None], ANIMAL_COST.to(dev)[(itc - 9).clamp(0, 2)][None].expand(B, -1), unit_cost)
    unit_cost = torch.where((kop == O.MKT_BUY_PRODUCT)[None], prices[:, itc.clamp(max=8)] * 12 // 10, unit_cost)
    cost = unit_cost[..., None] * qty                                                                          # [B,K,R]
    cost = torch.where((kop == O.MKT_HIRE)[None, :, None], FIB.to(dev)[(hires0[:, None, None] + r).clamp(max=20)].expand(-1, K, -1), cost)
    cost = torch.where((kop == O.MKT_BUY_LAND)[None, :, None], LAND_COST.to(dev)[(land0[:, None, None] + r).clamp(max=3)].expand(-1, K, -1), cost)
    want = want.reshape(B, -1); cost = cost.reshape(B, -1); qty = qty.reshape(B, -1)
    cum = torch.cumsum(cost * want, 1)
    ok = want & (cum <= money[:, None])
    rank = torch.cumsum(ok.long(), 1) - 1
    ok = ok & (rank < O.MAX_ORDERS)
    val = torch.stack([kop[:, None].expand(-1, R).reshape(1, -1).expand(B, -1), kit[:, None].expand(-1, R).reshape(1, -1).expand(B, -1), qty], -1)
    dst = torch.where(ok, rank, torch.full_like(rank, O.MAX_ORDERS))
    buf = torch.zeros((B, O.MAX_ORDERS + 1, 3), dtype=torch.long, device=dev)
    buf.scatter_(1, dst[..., None].expand(-1, -1, 3), val * ok[..., None])
    orders = buf[:, :O.MAX_ORDERS]
    return farmer, hands, orders


def combine(a0, a1):
    """two players' (farmer, hands, market) -> gpuenv Actions."""
    f = torch.stack([a0[0], a1[0]], 1).to(torch.int16); h = torch.stack([a0[1], a1[1]], 1).to(torch.int16); m = torch.stack([a0[2], a1[2]], 1).to(torch.int16)
    return Actions(f, h, m)
