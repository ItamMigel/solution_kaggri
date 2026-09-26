"""Flow-matching plan layer: each day sample tomorrow's macro target from a conditional flow-matching model learned on top teams'
day transitions (research/re/fm_top_model.json), then lay the target counts onto tiles. Same interface as plan.py."""
import json, math, random
try:
    import numpy as _np
except Exception:
    _np = None
FM = None  # filled by bundle (FM_MODEL json)
CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]; AN = ["COW", "SHEEP", "GOOSE"]
SHOPS = ["BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE", "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET"]
ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]
_CACHE = {}
HORIZON = 1
USE_MPC = True
def _silu(v): return [a / (1.0 + math.exp(-a)) if a > -60 else 0.0 for a in v]
def _lin(W, b, v): return [sum(w * x for w, x in zip(row, v)) + bb for row, bb in zip(W, b)]
def _net(inp):
    h = inp; L = FM["W"]
    for k, (W, b) in enumerate(L):
        h = _lin(W, b, h)
        if k < len(L) - 1: h = _silu(h)
    return h
MPC_K, MPC_M, MPC_STEPS, MPC_LAM = 4, 8, 6, 1.0
_NPW = None
def _np_weights():
    global _NPW
    if _NPW is None:
        _NPW = [(_np.array(W, dtype=_np.float32), _np.array(b, dtype=_np.float32)) for W, b in FM["W"]]
    return _NPW
def _np_net(inp):
    h = inp; L = _np_weights()
    for k, (W, b) in enumerate(L):
        h = h @ W.T + b
        if k < len(L) - 1: h = h / (1.0 + _np.exp(-_np.clip(h, -60, 60)))
    return h
def _np_step(cur, day, shops, op, rng, steps):
    """One FM day-transition for a batch of macro states cur (N x D)."""
    mu_x = _np.array(FM["mu_x"], _np.float32); sd_x = _np.array(FM["sd_x"], _np.float32)
    mu_d = _np.array(FM["mu_d"], _np.float32); sd_d = _np.array(FM["sd_d"], _np.float32)
    n = cur.shape[0]; xn = (cur - mu_x) / sd_x
    cond = _np.concatenate([xn, _np.full((n, 1), min(29, day) / 29.0, _np.float32), _np.tile(_np.array(shops + op, _np.float32), (n, 1))], 1)
    z = rng.standard_normal((n, len(FM["mu_d"]))).astype(_np.float32)
    for k in range(steps):
        z = z + _np_net(_np.concatenate([z, _np.full((n, 1), k / steps, _np.float32), cond], 1)) / steps
    return cur + z * sd_d + mu_d
def _mpc_target(me, day, shops, op, seed):
    rng = _np.random.default_rng(seed)
    cur = _np.tile(_np.array(me, _np.float32), (MPC_K, 1))
    cand = _np_step(cur, day, shops, op, rng, MPC_STEPS)                      # K candidate tomorrows
    roll = _np.repeat(cand, MPC_M, 0)
    for dd in range(day + 1, 29):                                           # Monte-Carlo futures to the end of the season
        roll = _np_step(roll, dd, shops, op, rng, MPC_STEPS)
    final_money = _np.expm1(_np.clip(roll[:, 12], 0, 20)).reshape(MPC_K, MPC_M)  # index 12 = log_money
    score = final_money.mean(1) - MPC_LAM * final_money.std(1)
    # trust region: penalise candidates far from the typical (mean) candidate in normalised units
    sd = _np.array(FM["sd_d"], _np.float32); dev = _np.abs((cand - cand.mean(0)) / sd).mean(1)
    score = score - 20000.0 * dev
    return list(map(float, cand[int(_np.argmax(score))]))

def _farm_macro(farm):
    t = {}; an = {}; st = {"PASTURE": 0, "COOP": 0}; fert = 0; empty = 0
    for row in farm["tiles"]:
        for x in row:
            if x is None: empty += 1
            elif isinstance(x, dict):
                k = x.get("kind")
                if k == "PLANT": t[x["crop"]] = t.get(x["crop"], 0) + 1; fert += x.get("fertilized_until_day", -1) >= 0
                elif k in st:
                    st[k] += 1
                    if x.get("animal"): an[x["animal"]] = an.get(x["animal"], 0) + 1
    return [t.get(c, 0) for c in CROPS] + [an.get(a, 0) for a in AN] + [st["PASTURE"], st["COOP"], len(farm.get("unlocked_quadrants") or ["NW"]),
            len(farm.get("hands") or []), math.log1p(max(0.0, float(farm["money"]))), fert, empty]
def _target(obs, player):
    day = int(obs["day"]); key = (player, day)
    if key in _CACHE: return _CACHE[key]
    me = _farm_macro(obs["farms"][player]); op = _farm_macro(obs["farms"][1 - player])
    shops = [sum(1 for s in (obs.get("town") or {}).get("unlocked_shops", []) if s == k) for k in SHOPS]
    if USE_MPC and _np is not None and day < 28:
        tgt = _mpc_target(me, day, shops, op, 1000 * day + player); _CACHE[key] = tgt; return tgt
    rnd = random.Random(1000 * day + player); D = len(FM["mu_d"]); S = 3; steps = 10; cur = list(me)
    for h in range(HORIZON):     # roll the day-transition flow forward HORIZON days from our current state
        xn = [(a - m) / s for a, m, s in zip(cur, FM["mu_x"], FM["sd_x"])]; cond = xn + [min(29, day + h) / 29.0] + shops + op
        acc = [0.0] * D
        for _ in range(S):
            z = [rnd.gauss(0, 1) for _ in range(D)]
            for k in range(steps):
                v = _net(z + [k / steps] + cond); z = [a + b / steps for a, b in zip(z, v)]
            acc = [a + b / S for a, b in zip(acc, z)]
        cur = [m + a * s + d for a, m, s, d in zip(acc, FM["mu_d"], FM["sd_d"], cur)]
    tgt = cur
    _CACHE[key] = tgt; return tgt
def _quad(t): return ("N" if t[1] < 5 else "S") + ("W" if t[0] < 5 else "E")
def _dist(t): return min(abs(t[0] - a) + abs(t[1] - b) for a, b in ACCESS)
def desired(obs, player):
    tg = _target(obs, player); day = int(obs["day"]); farm = obs["farms"][player]; tiles = farm["tiles"]
    want_crop = {c: max(0, int(round(tg[i]))) for i, c in enumerate(CROPS)}
    want_an = {a: max(0, int(round(tg[5 + i]))) for i, a in enumerate(AN)}
    owned = [(x, y) for y in range(10) for x in range(10) if tiles[y][x] != "LOCKED"]
    want = {}; have = {c: 0 for c in CROPS}; have_an = {"COW": 0, "SHEEP": 0, "GOOSE": 0}; free = []
    for (x, y) in owned:     # keep what exists: crops keep their role, animal structures keep their animal
        t = tiles[y][x]
        if isinstance(t, dict) and t.get("kind") == "PLANT": want[(x, y)] = t["crop"]; have[t["crop"]] += 1
        elif isinstance(t, dict) and t.get("kind") in ("PASTURE", "COOP"):
            a = t.get("animal") or ("GOOSE" if t["kind"] == "COOP" else ("COW" if have_an["COW"] < want_an["COW"] else "SHEEP"))
            want[(x, y)] = t["kind"] + ":" + a; have_an[a] += 1
        else: free.append((x, y))
    free.sort(key=lambda t: (_dist(t), t[1], t[0]))
    for a in ("COW", "SHEEP", "GOOSE"):   # new structures next to the shed
        for _ in range(max(0, want_an[a] - have_an[a])):
            if not free: break
            t = free.pop(0); want[t] = ("COOP:" if a == "GOOSE" else "PASTURE:") + a
    if day >= 28: return want
    order = sorted(CROPS, key=lambda c: -(want_crop[c] - have[c]))
    for c in order:
        for _ in range(max(0, want_crop[c] - have[c])):
            if not free: break
            want[free.pop(0)] = c
    return want
def targets(obs, player):
    tg = _target(obs, player); step = int(obs.get("step", 0)); q = len(obs["farms"][player].get("unlocked_quadrants") or ["NW"])
    land = {}
    if tg[10] > q + 0.35: land[q + 1] = step          # model wants more land now
    return {"hands": max(3, min(12, int(round(tg[11])))) if int(obs["day"]) < 29 else 8, "land_step": land, "wheat_reserve_per_animal": 2}
