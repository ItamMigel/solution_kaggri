

# ================= HG: herd guard for the BC agent (lab/pavel, 2026-09-29) =================
# Prevents animal escapes (engine: an animal unfed on two consecutive days leaves its structure).
# 1) If an animal that was unfed yesterday is still unfed today, and the nearest unit only just has enough
#    turns left to fetch wheat (shed-adjacent PICKUP) and walk to it, that unit is overridden to feed it.
# 2) Keeps shed wheat >= herd size at the start of each day by an appended BUY_PRODUCT WHEAT (cash permitting);
#    under an urgent shortage it also drops the policy's own WHEAT sales.
_HG = {'on': True, 'slack': 3, 'buy_on': True, 'stock_hours': (0, 1, 2), 'stock_frac': 1.0, 'max_buy': 30,
       'cash_keep': 0, 'last_day': 29}
_HG_STATS = {'overrides': 0, 'buy_turns': 0, 'buy_units': 0, 'dropped_sells': 0, 'errors': 0}
_HG_SHED = [(4, 4), (5, 4), (4, 5), (5, 5)]


def _hg_d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _hg_mv(x, y, tx, ty):
    if tx > x: return "EAST"
    if tx < x: return "WEST"
    if ty > y: return "SOUTH"
    if ty < y: return "NORTH"
    return "PASS"


def _hg_apply(obs, action):
    p = int(obs["player"]); step = int(obs["step"]); day = step // 24; hour = step % 24
    if step >= 718 or day > int(_HG.get("active_last_day", 29)):
        return action
    farm = obs["farms"][p]; tiles = farm["tiles"]; priv = obs.get("private") or {}
    shed = priv.get("shed") or {}; invs = priv.get("inventories") or []
    animals = [(x, y, tiles[y][x]) for y in range(10) for x in range(10)
               if isinstance(tiles[y][x], dict) and tiles[y][x].get("animal")]
    if not animals:
        return action
    pos = [tuple(farm["farmer"])] + [tuple(h) for h in (farm.get("hands") or [])]
    acts = [list(action.get("farmer") or ["PASS"])] + [list(a) for a in (action.get("hands") or [])]
    while len(acts) < len(pos):
        acts.append(["PASS"])
    carried = [int((invs[i] if i < len(invs) else {}).get("WHEAT", 0) or 0) for i in range(len(pos))]
    shed_w = int(shed.get("WHEAT", 0) or 0)
    urgent_all = [(x, y) for x, y, t in animals if int(t.get("consecutive_unfed", 0) or 0) >= 1 and not t.get("fed_today")]
    urgent = list(urgent_all)
    for i, a in enumerate(acts):
        if a and a[0] == "FEED" and pos[i] in urgent and carried[i] > 0:
            urgent.remove(pos[i]); carried[i] -= 1
    changed = False
    free = set(range(len(pos)))
    for ax, ay in urgent:
        best = None
        for i in free:
            if carried[i] > 0:
                cost = _hg_d(pos[i], (ax, ay)) + 1
            elif shed_w > 0:
                s = min(_HG_SHED, key=lambda c: (_hg_d(pos[i], c) + _hg_d(c, (ax, ay)), c))
                cost = _hg_d(pos[i], s) + 1 + _hg_d(s, (ax, ay)) + 1
            else:
                continue
            if best is None or cost < best[0]:
                best = (cost, i)
        if best is None:
            continue
        cost, i = best
        if hour + cost + int(_HG["slack"]) < 24:
            continue
        free.discard(i)
        if carried[i] > 0:
            new = ["FEED"] if pos[i] == (ax, ay) else [_hg_mv(pos[i][0], pos[i][1], ax, ay)]
            carried[i] -= 1
        elif pos[i] in _HG_SHED:
            n = max(1, min(shed_w, len(urgent))); new = ["PICKUP", "WHEAT", n]; shed_w -= n
        else:
            s = min(_HG_SHED, key=lambda c: (_hg_d(pos[i], c) + _hg_d(c, (ax, ay)), c))
            new = [_hg_mv(pos[i][0], pos[i][1], s[0], s[1])]
        if new != acts[i]:
            acts[i] = new; changed = True; _HG_STATS["overrides"] += 1
    market = [list(o) if isinstance(o, (list, tuple)) else o for o in (action.get("market") or [])]
    if _HG["buy_on"] and day <= int(_HG["last_day"]):
        have = int(shed.get("WHEAT", 0) or 0) + sum(int((iv or {}).get("WHEAT", 0) or 0) for iv in invs)
        need = 0
        if hour in _HG["stock_hours"]:
            need = int(len(animals) * float(_HG["stock_frac"]) + 0.999)
        if urgent_all:
            need = max(need, len(urgent_all))
        deficit = need - have
        if deficit > 0:
            if urgent_all and have < len(urgent_all):
                kept = []
                for o in market:
                    if isinstance(o, list) and len(o) >= 2 and o[0] == "SELL" and o[1] == "WHEAT":
                        _HG_STATS["dropped_sells"] += 1; continue
                    kept.append(o)
                market = kept
            price = max(1, int(((obs.get("market") or {}).get("prices") or {}).get("WHEAT", 30) or 30))
            money = int(float(farm.get("money", 0)))
            q = min(int(_HG["max_buy"]), deficit, max(0, (money - int(_HG["cash_keep"])) // (price + 2)))
            has_buy = [o for o in market if isinstance(o, list) and len(o) >= 3 and o[0] == "BUY_PRODUCT" and o[1] == "WHEAT"]
            if q > 0:
                if has_buy:
                    if int(has_buy[0][2]) < q:
                        has_buy[0][2] = q; _HG_STATS["buy_turns"] += 1; _HG_STATS["buy_units"] += q
                elif len(market) < 10:
                    market.insert(0, ["BUY_PRODUCT", "WHEAT", q]); _HG_STATS["buy_turns"] += 1; _HG_STATS["buy_units"] += q
            changed = True
    if not changed:
        return action
    return {"farmer": acts[0], "hands": acts[1:len(pos)], "market": market}


_HG_PARENT = agent
del agent


def agent(obs, config=None):
    action = _HG_PARENT(obs, config)
    if not _HG["on"]:
        return action
    try:
        return _hg_apply(obs, action)
    except Exception:
        _HG_STATS["errors"] += 1
        return action

agent.telemetry = _HG_STATS
