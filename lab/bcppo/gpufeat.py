"""Batched torch mirror of lab/bc/feat.py: gpuenv State -> (board, glob, units) for a given player.
Must match feat.py exactly (tested by parity_test.py). Shapes:
  board [B, C_BOARD, 10, 10] float32
  glob  [B, G_DIM] float32               (team one-hot is appended by the caller)
  uvec  [B, U, U_DIM], ux/uy [B, U] long, umask [B, U] bool   (U = 1 + MAX_HANDS)
The first-two-shops feature needs unlock ORDER, which State does not keep: ShopOrder tracks it across steps."""
import os, sys
import torch
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bc")); sys.path.insert(0, os.path.join(HERE, ".."))
import feat
from gpuenv import ops as O

N = 10
FIRST_YIELD = torch.tensor([feat.FIRST_YIELD[c] for c in feat.CROPS])
BASE = torch.tensor([feat.BASE_PRICE[p] for p in feat.PRODUCTS], dtype=torch.float32)
SHED_ADJ_MASK = torch.zeros(N * N, dtype=torch.bool)
for (x, y) in feat.SHED_ADJ:
    SHED_ADJ_MASK[y * N + x] = True
YARN = feat.SHOPS.index("YARN_STORE")


class ShopOrder:
    """Tracks the first two unlocked shops (alphabetical index) per env, since State only stores counts."""
    def __init__(self, B, dev):
        self.first = torch.full((B, 2), -1, dtype=torch.long, device=dev); self.prev = torch.zeros((B, 8), dtype=torch.long, device=dev)
    def reset(self):
        self.first.fill_(-1); self.prev.zero_()
    def update(self, st):
        cur = st.shops.to(torch.long); new = (cur - self.prev).clamp(min=0)
        idx = new.argmax(1); has = new.sum(1) > 0
        slot0 = has & (self.first[:, 0] < 0); slot1 = has & ~slot0 & (self.first[:, 1] < 0)
        self.first[:, 0] = torch.where(slot0, idx, self.first[:, 0]); self.first[:, 1] = torch.where(slot1, idx, self.first[:, 1])
        self.prev = cur.clone()


def features(st, p, shop_order):
    dev = st.money.device; B = st.money.shape[0]
    step = int(st.step); day = step // 24; hour = step % 24
    q = 1 - p
    kind = st.kind[:, p].long(); sp = st.species[:, p].long()
    Bd = torch.zeros((B, feat.C_BOARD, N * N), device=dev)
    Bd[:, 0] = (kind == O.TILE_EMPTY).float(); Bd[:, 1] = (kind == O.TILE_LOCKED).float(); Bd[:, 2] = (kind == O.TILE_WEED).float()
    plant = kind == O.TILE_PLANT
    for c in range(5):
        Bd[:, 3 + c] = (plant & (sp == c)).float()
    age = day - st.tday[:, p].long()
    Bd[:, 8] = torch.where(plant, age.float() / 10.0, 0.0)
    Bd[:, 29] = torch.where(plant, (age >= FIRST_YIELD.to(dev)[sp.clamp(0, 4)]).float(), 0.0)
    flag = st.tflag[:, p]; yld = st.tyield[:, p].float(); cons = st.tcons[:, p].float()
    Bd[:, 9] = (plant & flag).float(); Bd[:, 10] = torch.where(plant, yld / 10.0, 0.0)
    Bd[:, 11] = (plant & (st.tfert[:, p].long() >= day)).float(); Bd[:, 12] = torch.where(plant, cons, 0.0)
    animal = kind == O.TILE_ANIMAL
    coop = (kind == O.TILE_COOP) | (animal & (sp == 0)); past = (kind == O.TILE_PASTURE) | (animal & (sp > 0))
    Bd[:, 13] = coop.float(); Bd[:, 14] = past.float()
    for a in range(3):
        Bd[:, 15 + a] = (animal & (sp == a)).float()
    Bd[:, 18] = (animal & flag).float(); Bd[:, 19] = (animal & st.tcared[:, p]).float()
    Bd[:, 20] = torch.where(animal, yld / 10.0, 0.0); Bd[:, 21] = (animal & st.tfavail[:, p]).float() / 5.0
    Bd[:, 22] = torch.where(animal, st.tcare[:, p].float() / 5.0, 0.0); Bd[:, 23] = torch.where(animal, cons, 0.0)
    ux = st.ux[:, p].long(); uy = st.uy[:, p].long(); U = ux.shape[1]
    nh = st.n_hands[:, p].long(); umask = torch.arange(U, device=dev)[None, :] <= nh[:, None]
    cell = uy * N + ux
    Bd[:, 24].scatter_(1, cell[:, :1], 1.0)
    hands_cnt = torch.zeros((B, N * N), device=dev).scatter_add_(1, cell[:, 1:], umask[:, 1:].float())
    Bd[:, 25] = hands_cnt; Bd[:, 26] = SHED_ADJ_MASK.to(dev).float()[None]
    ar = torch.arange(N, device=dev).float() / 9.0
    Bd[:, 27] = ar[None, None, :].expand(B, N, N).reshape(B, -1); Bd[:, 28] = ar[None, :, None].expand(B, N, N).reshape(B, -1)
    board = Bd.view(B, feat.C_BOARD, N, N)

    money = st.money.float()
    prices = st.market_price().float()
    g = [torch.full((B,), step / 719.0, device=dev), torch.full((B,), hour / 23.0, device=dev), torch.full((B,), day / 29.0, device=dev),
         money[:, p] / 5e4, money[:, q] / 5e4, torch.log1p(money[:, p].clamp(min=0)) / 12.0]
    G = torch.stack(g, 1)
    G = torch.cat([G, prices / BASE.to(dev), (10000.0 - st.market_inv.float()) / 500.0,
                   st.shed[:, p].float() / 50.0, st.seeds[:, p].float() / 20.0,
                   torch.stack([st.hires_today[:, p].float() / 15.0, nh.float() / 15.0, (1 + st.land[:, p].float()) / 4.0,
                                st.n_hands[:, q].float() / 15.0], 1),
                   st.shops.float() / 2.0,
                   ((shop_order.first == YARN).any(1)).float()[:, None]], 1)
    for f in (p, q):
        k = st.kind[:, f].long(); s = st.species[:, f].long()
        herd = torch.stack([((k == O.TILE_ANIMAL) & (s == a)).sum(1) for a in range(3)], 1).float() / 10.0
        pl = torch.stack([((k == O.TILE_PLANT) & (s == c)).sum(1) for c in range(5)], 1).float() / 20.0
        G = torch.cat([G, herd, pl], 1)

    inv = st.inv[:, p].float()  # [B, U, 12]
    uv = torch.cat([(torch.arange(U, device=dev) == 0).float()[None, :, None].expand(B, U, 1), ux.float()[..., None] / 9.0, uy.float()[..., None] / 9.0,
                    SHED_ADJ_MASK.to(dev)[cell].float()[..., None], inv / 10.0, inv.sum(-1, keepdim=True) / 20.0], -1)
    return board, G, uv, ux, uy, umask
