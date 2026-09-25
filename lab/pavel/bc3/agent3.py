"""Closed-loop BC v3 agent (torch on CPU; local evaluation only, not a Kaggle submission format yet).
make_agent_dir(ckpt, out_dir, sample=False, temp=1.0) writes out_dir/main.py + model.pt usable by compare.py / replay_eval.py.

Decoding mirrors lab/bc/export.py (legality masks per engine semantics, target cell + greedy pathing), plus v3 heads:
PICKUP/PLACE quantity head and an autoregressive 10-slot market decoder (tokens incl. NOOP, END)."""
import os, shutil, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feat3 as F  # noqa: E402

_MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}
_STRUCT = {"GOOSE": "COOP", "COW": "PASTURE", "SHEEP": "PASTURE"}
_MAX_HANDS = 16
SHED_ADJ = {(4, 4), (5, 4), (4, 5), (5, 5)}


def _tile_mask(obs, p, x, y, inv, day):
    """Copy of lab/bc/export.py _tile_mask (engine _apply_unit_action semantics); PLANT/PICKUP set by caller."""
    t = obs["farms"][p]["tiles"][y][x]; m = np.zeros(len(F.UNIT_OPS), bool); inv = inv or {}
    for mv, (dx, dy) in _MOVES.items():
        m[F.UNIT_IDX[mv]] = 0 <= x + dx < 10 and 0 <= y + dy < 10
    locked = t == "LOCKED"; empty = t is None
    d = t if isinstance(t, dict) else {}
    plant = d.get("kind") == "PLANT"; animal = "animal" in d and d.get("animal") is not None
    if plant:
        age = day - int(d.get("planted_day", day)); fy = F.feat.FIRST_YIELD.get(d.get("crop"), 99)
        m[F.UNIT_IDX["WATER"]] = not d.get("watered_today")
        m[F.UNIT_IDX["HARVEST"]] = age >= fy and int(d.get("yield_units", 0)) > 0
        m[F.UNIT_IDX["FERTILIZE"]] = inv.get("FERTILIZER", 0) > 0
    if animal:
        m[F.UNIT_IDX["HARVEST"]] = int(d.get("yield_units", 0)) > 0
        m[F.UNIT_IDX["FEED"]] = (not d.get("fed_today")) and inv.get("WHEAT", 0) > 0
        m[F.UNIT_IDX["CARE"]] = not d.get("cared_today")
        m[F.UNIT_IDX["COLLECT_FERTILIZER"]] = bool(d.get("fertilizer_available"))
    m[F.UNIT_IDX["BUILD_COOP"]] = m[F.UNIT_IDX["BUILD_PASTURE"]] = empty
    m[F.UNIT_IDX["DIG"]] = (not empty) and (not locked) and (not animal)
    adj = (x, y) in SHED_ADJ
    m[F.UNIT_IDX["DROP"]] = adj and sum(inv.values()) > 0
    for it in F.ITEMS:
        has = inv.get(it, 0) > 0
        if it in _STRUCT:
            m[F.UNIT_IDX["PLACE:" + it]] = has and ((d.get("kind") == _STRUCT[it] and not animal) or adj)
        else:
            m[F.UNIT_IDX["PLACE:" + it]] = has and adj
    m[F.UNIT_IDX["PASS"]] = True
    return m, (empty and not locked), adj


def _step_toward(x, y, tx, ty):
    if tx > x: return "EAST"
    if tx < x: return "WEST"
    if ty > y: return "SOUTH"
    if ty < y: return "NORTH"
    return None


def _filler(obs, p, x, y, inv, day, claimed, shed_left):
    """Scripted fallback for a unit whose model choice was illegal (forced PASS): do useful maintenance work."""
    tiles = obs["farms"][p]["tiles"]; inv = inv or {}
    t = tiles[y][x]; d = t if isinstance(t, dict) else {}
    wheat = int(inv.get("WHEAT", 0))
    # 1) work on the current tile
    if d.get("kind") == "PLANT":
        age = day - int(d.get("planted_day", day)); fy = F.feat.FIRST_YIELD.get(d.get("crop"), 99)
        if not d.get("watered_today"): return ["WATER"]
        if age >= fy and int(d.get("yield_units", 0)) > 0: return ["HARVEST"]
    if d.get("animal"):
        if d.get("fertilizer_available"): return ["COLLECT_FERTILIZER"]
        if int(d.get("yield_units", 0)) > 0: return ["HARVEST"]
        if not d.get("fed_today") and wheat > 0: return ["FEED"]
        if not d.get("cared_today"): return ["CARE"]
    adj = (x, y) in SHED_ADJ
    products = {k: v for k, v in inv.items() if v and k not in ("WHEAT", "FERTILIZER") and k not in _STRUCT}
    if adj and products: return ["DROP"]
    # 2) scan the farm
    unfed, water, harvest, collect = [], [], [], []
    for yy in range(10):
        for xx in range(10):
            tt = tiles[yy][xx]
            if not isinstance(tt, dict) or (xx, yy) in claimed: continue
            if tt.get("animal"):
                if not tt.get("fed_today"): unfed.append((xx, yy))
                if tt.get("fertilizer_available") or int(tt.get("yield_units", 0)) > 0: collect.append((xx, yy))
            elif tt.get("kind") == "PLANT":
                if not tt.get("watered_today"): water.append((xx, yy))
                age = day - int(tt.get("planted_day", day))
                if age >= F.feat.FIRST_YIELD.get(tt.get("crop"), 99) and int(tt.get("yield_units", 0)) > 0: harvest.append((xx, yy))
    near = lambda cells: min(cells, key=lambda c: abs(c[0] - x) + abs(c[1] - y)) if cells else None
    if unfed and wheat > 0:
        c = near(unfed); claimed.add(c); return [_step_toward(x, y, *c)]
    if unfed and wheat == 0 and shed_left.get("WHEAT", 0) > 0:
        if adj:
            n = max(1, min(len(unfed), shed_left["WHEAT"])); shed_left["WHEAT"] -= n; return ["PICKUP", "WHEAT", n]
        c = near(sorted(SHED_ADJ)); return [_step_toward(x, y, *c)]
    for cells in (water, harvest, collect):
        c = near(cells)
        if c is not None:
            claimed.add(c); return [_step_toward(x, y, *c)]
    if products:
        c = near(sorted(SHED_ADJ)); m = _step_toward(x, y, *c)
        if m: return [m]
    return None


class Agent:
    def __init__(self, ckpt, sample=False, temp=1.0, seed=12345, persist=False, dedupe=False, msample=False, fill=False,
                 smask=False, notrip=False):
        import torch
        torch.set_num_threads(1)
        from train3 import Net
        ck = torch.load(ckpt, map_location="cpu", weights_only=False)
        self.net = Net(**ck["cfg"]); sd = ck["state"]
        w = sd["m_ctx.0.weight"]; need = self.net.m_ctx[0].weight.shape[1]
        if w.shape[1] < need:  # checkpoint trained before the shed-after-units market input: zero weights = old behaviour
            sd["m_ctx.0.weight"] = torch.cat([w, torch.zeros(w.shape[0], need - w.shape[1])], 1)
        self.net.load_state_dict(sd); self.net.eval()
        self.torch = torch; self.sample = sample; self.temp = temp; self.rng = np.random.default_rng(seed)
        self.snaps = []; self.last_step = None
        self.persist = persist; self.dedupe = dedupe; self.tgt = {}; self.tgt_day = -1; self.msample = msample; self.fill = fill; self.smask = smask; self.notrip = notrip
        self.stats = {"n": 0, "pass": 0, "pass_forced": 0, "at_tgt_wants_move": 0, "top_masked": 0} if os.environ.get("BC3_STATS") else None

    def _pick(self, logits, mask=None, market=False):
        z = np.asarray(logits, np.float64)
        if mask is not None:
            z = np.where(mask, z, -1e9)
        if not (self.sample or (market and self.msample)):
            return int(z.argmax())
        g = -np.log(-np.log(self.rng.random(z.shape) + 1e-20) + 1e-20)
        return int((z / self.temp + g).argmax())

    def __call__(self, obs, config=None):
        torch = self.torch
        p = int(obs.get("player", 0)); step = int(obs.get("step", 0)); day = int(obs.get("day", step // 24))
        if self.last_step is None or step <= self.last_step:
            self.snaps = []; self.tgt = {}
        if day != self.tgt_day:
            self.tgt = {}; self.tgt_day = day
        self.last_step = step
        self.snaps.append(F.snapshot(obs, p)); self.snaps = self.snaps[-(F.LAGS + 1):]
        Bd = F.board3(obs, p); g = F.glob3(obs, p, F.hist_features(self.snaps)); ul = F.units3(obs, p)
        priv = obs.get("private") or {}; invs = priv.get("inventories") or []
        farm = obs["farms"][p]
        with torch.no_grad():
            B = torch.from_numpy(Bd[None]).float(); G = torch.from_numpy(g[None])
            h = self.net.trunk(B, G)
            acts = []
            if ul:
                bi = torch.zeros(len(ul), dtype=torch.long)
                ux = torch.tensor([u[0] for u in ul]); uy = torch.tensor([u[1] for u in ul])
                uv = torch.from_numpy(np.stack([u[2] for u in ul]))
                z0 = torch.cat([h[bi, :, uy, ux], uv, G[bi]], 1); z = self.net.unit(z0)
                opl = self.net.u_op(z).numpy()
                tl = (torch.einsum("uc,ucp->up", self.net.tq(z0), h.flatten(2)[bi]) / (h.shape[1] ** 0.5)).numpy()
                seeds_left = {c: int((priv.get("seeds") or {}).get(c, 0)) for c in F.CROPS}
                shed_left = {it: int((priv.get("shed") or {}).get(it, 0)) for it in F.ITEMS}
                claimed = set()
                for i, (x, y, _v) in enumerate(ul):
                    inv = invs[i] if i < len(invs) else {}
                    mu, empty_ok, adj = _tile_mask(obs, p, x, y, inv, day)
                    for c in F.CROPS:
                        mu[F.UNIT_IDX["PLANT:" + c]] = empty_ok and seeds_left[c] > 0
                    for it in F.ITEMS:
                        mu[F.UNIT_IDX["PICKUP:" + it]] = adj and shed_left[it] > 0
                    if self.persist and i in self.tgt and self.tgt[i] != (x, y):
                        tx, ty = self.tgt[i]
                    else:
                        tlog = tl[i].copy()
                        if self.dedupe:
                            for (cx, cy) in claimed:
                                if (cx, cy) not in SHED_ADJ and (cx, cy) != (x, y):
                                    tlog[cy * 10 + cx] = -1e9
                        tgt = self._pick(tlog); tx, ty = tgt % 10, tgt // 10
                    claimed.add((tx, ty))
                    if (tx, ty) != (x, y):
                        self.tgt[i] = (tx, ty)
                    else:
                        self.tgt.pop(i, None)
                    want = np.zeros(len(F.UNIT_OPS), bool)
                    want[F.UNIT_IDX["EAST"]] = tx > x; want[F.UNIT_IDX["WEST"]] = tx < x
                    want[F.UNIT_IDX["SOUTH"]] = ty > y; want[F.UNIT_IDX["NORTH"]] = ty < y
                    mv = want & mu
                    if (tx, ty) != (x, y) and mv.any():
                        mask = mv
                    else:
                        mask = mu.copy()
                        for k in _MOVES:
                            mask[F.UNIT_IDX[k]] = False
                    cls = self._pick(opl[i], mask); k = F.UNIT_OPS[cls]
                    if self.stats is not None:
                        top = int(np.argmax(opl[i])); st = self.stats
                        st["n"] += 1; st["pass"] += k == "PASS"
                        st["pass_forced"] += (k == "PASS") and (F.UNIT_OPS[top] != "PASS")
                        st["at_tgt_wants_move"] += ((tx, ty) == (x, y)) and (F.UNIT_OPS[top] in _MOVES)
                        st["top_masked"] += not mask[top]
                    if self.fill and k == "PASS" and F.UNIT_OPS[int(np.argmax(opl[i]))] != "PASS":
                        fa = _filler(obs, p, x, y, inv, day, claimed, shed_left)
                        if fa is not None and fa[0] is not None:
                            acts.append(fa)
                            if self.stats is not None: self.stats["filled"] = self.stats.get("filled", 0) + 1
                            continue
                    if k.startswith("PLANT:"):
                        seeds_left[k[6:]] -= 1; acts.append(["PLANT", k[6:]])
                    elif k.startswith("PICKUP:") or k.startswith("PLACE:"):
                        oh = torch.zeros(1, len(F.UNIT_OPS)); oh[0, cls] = 1
                        ql = self.net.u_q(torch.cat([z[i:i + 1], oh], 1)).numpy()[0]
                        n = F.QTY_VALS[self._pick(ql)]; op, it = k.split(":")
                        if op == "PICKUP":
                            n = max(1, min(n, shed_left[it])); shed_left[it] -= n
                        acts.append([op, it, n])
                    else:
                        acts.append([k])
            # market: autoregressive slot decoding
            n_hands = len(farm.get("hands") or []); hires = 0
            lands_left = max(0, 3 - (len(farm.get("unlocked_quadrants") or []) - 1)); lands = 0
            ms = F.shed_after_units(obs, p, acts)
            sell_left = {it: int(round(v * 50)) for it, v in zip(F.ITEMS, ms)}
            MS = torch.from_numpy(ms[None])
            ctx = self.net.m_context(h, G, MS); state = ctx
            prev_t = torch.tensor([F.N_TOK]); prev_q = torch.tensor([F.QMAX]); orders = []; sold = set()
            for sl in range(F.N_SLOTS):
                state, logit = self.net.m_step(state, ctx, prev_t, prev_q, torch.tensor([sl]))
                mask = np.ones(F.N_TOK, bool)
                mask[F.TOK_IDX["HIRE"]] = n_hands + hires < _MAX_HANDS
                mask[F.TOK_IDX["BUY_LAND"]] = lands < lands_left
                if self.smask:  # SELL only what is in the shed at market time; units bought this turn are NOT sellable
                    for it in F.PRODUCTS:
                        mask[F.TOK_IDX["SELL:" + it]] = sell_left.get(it, 0) > 0
                if self.notrip:  # no intra-turn round trips: no BUY of an item already sold this turn
                    for it in ("WHEAT", "FERTILIZER"):
                        if it in sold:
                            mask[F.TOK_IDX["BUY_PRODUCT:" + it]] = False
                tok = self._pick(logit.numpy()[0], mask, market=True); key = F.TOKENS[tok]
                if key == "END":
                    break
                if key in ("NOOP", "HIRE", "BUY_LAND"):
                    orders.append([key]); q = F.QMAX
                    hires += key == "HIRE"; lands += key == "BUY_LAND"
                else:
                    ql = self.net.m_qty(state, torch.tensor([tok])).numpy()[0]; q = self._pick(ql, market=True)
                    op, it = key.split(":"); n = q + 1
                    if op == "SELL":
                        sold.add(it)
                        if self.smask:
                            n = max(1, min(n, sell_left.get(it, 0))); sell_left[it] -= n
                    orders.append([op, it, n])
                prev_t = torch.tensor([tok]); prev_q = torch.tensor([q])
        return {"farmer": acts[0] if acts else ["PASS"], "hands": acts[1:], "market": orders}


MAIN_TEMPLATE = '''"""BC v3 agent (local evaluation). Generated by lab/pavel/bc3/agent3.py."""
import sys
sys.path.insert(0, {here!r})
import agent3 as _a3
_AG = _a3.Agent({ckpt!r}, sample={sample!r}, temp={temp!r}, seed={seed!r}, persist={persist!r}, dedupe={dedupe!r}, msample={msample!r}, fill={fill!r}, smask={smask!r}, notrip={notrip!r})


def agent(obs, config=None):
    try:
        return _AG(obs, config)
    except Exception:
        import traceback, sys as _s
        traceback.print_exc(file=_s.stderr)
        return {{"farmer": ["PASS"], "hands": [], "market": []}}
'''


def make_agent_dir(ckpt, out_dir, sample=False, temp=1.0, seed=12345, persist=False, dedupe=False, msample=False, fill=False,
                   smask=False, notrip=False):
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(os.path.abspath(out_dir), "model.pt"); shutil.copy(ckpt, dst)
    with open(os.path.join(out_dir, "main.py"), "w") as f:
        f.write(MAIN_TEMPLATE.format(here=HERE, ckpt=dst, sample=sample, temp=temp, seed=seed, persist=persist, dedupe=dedupe, msample=msample, fill=fill, smask=smask, notrip=notrip))
    return os.path.join(out_dir, "main.py")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--ckpt", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--sample", action="store_true"); ap.add_argument("--temp", type=float, default=1.0); ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--persist", action="store_true"); ap.add_argument("--dedupe", action="store_true"); ap.add_argument("--msample", action="store_true")
    ap.add_argument("--fill", action="store_true"); ap.add_argument("--smask", action="store_true"); ap.add_argument("--notrip", action="store_true")
    a = ap.parse_args(); print(make_agent_dir(a.ckpt, a.out, a.sample, a.temp, a.seed, a.persist, a.dedupe, a.msample, a.fill, a.smask, a.notrip))
