

# ================= TL: terminal liquidation for the BC agent (lab/pavel, 2026-09-30) =================
# Engine facts: the game ends after the market of step 718, before the end-of-day auto-drop, so products still in
# unit inventories are lost; SELL sells only from the shed; units act before the market in the same step; DROP needs a
# shed-adjacent tile and destroys what does not fit (shed capacity 100).
# 1) From route_from: a unit carrying products heads to the shed only when it would otherwise not get back in time
#    (remaining steps <= distance + slack) and DROPs there.
# 2) From sell_from: appends SELLs spreading the remaining shed stock over the remaining steps.
# 3) Step 718: market = SELL everything (shed + this step's drops), most valuable first.
_TL = {'on': True, 'route_from': 690, 'sell_from': 712, 'slack': 1, 'route': True, 'spread': True}
_TL_STATS = {'routes': 0, 'drops': 0, 'sell_turns': 0, 'final_turns': 0, 'errors': 0}
_TL_SHED = [(4, 4), (5, 4), (4, 5), (5, 5)]
_TL_PRODUCTS = ('WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON', 'EGG', 'MILK', 'WOOL', 'FERTILIZER')


def _tl_d(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _tl_mv(x, y, tx, ty):
    if tx > x: return "EAST"
    if tx < x: return "WEST"
    if ty > y: return "SOUTH"
    if ty < y: return "NORTH"
    return "PASS"


def _tl_apply(obs, action):
    step = int(obs["step"])
    if step < min(int(_TL["route_from"]), int(_TL["sell_from"])) or step > 718:
        return action
    p = int(obs["player"]); farm = obs["farms"][p]; priv = obs.get("private") or {}
    shed = {k: int(v or 0) for k, v in (priv.get("shed") or {}).items()}
    invs = priv.get("inventories") or []
    prices = ((obs.get("market") or {}).get("prices") or {})
    pos = [tuple(farm["farmer"])] + [tuple(h) for h in (farm.get("hands") or [])]
    acts = [list(action.get("farmer") or ["PASS"])] + [list(a) for a in (action.get("hands") or [])]
    while len(acts) < len(pos):
        acts.append(["PASS"])
    left = 718 - step
    changed = False
    if _TL["route"] and left <= int(_TL.get("no_pickup_last", 3)):
        for i, a in enumerate(acts):
            if a and a[0] == "PICKUP" and len(a) >= 2 and a[1] in _TL_PRODUCTS:
                acts[i] = ["PASS"]; changed = True; _TL_STATS["pickups_blocked"] = _TL_STATS.get("pickups_blocked", 0) + 1
    if _TL["route"] and step >= int(_TL["route_from"]):
        for i, (x, y) in enumerate(pos):
            inv = invs[i] if i < len(invs) else {}
            if not any(k in _TL_PRODUCTS and int(v or 0) > 0 for k, v in (inv or {}).items()):
                continue
            s = min(_TL_SHED, key=lambda c: (_tl_d((x, y), c), c)); d = _tl_d((x, y), s)
            if left > d + int(_TL["slack"]):
                continue
            new = ["DROP"] if d == 0 else [_tl_mv(x, y, s[0], s[1])]
            if acts[i] != new:
                acts[i] = new; changed = True
                _TL_STATS["drops" if d == 0 else "routes"] += 1
    # stock sellable in this step's market = shed + products dropped this step (limited by shed room)
    room = max(0, 100 - sum(max(0, v) for v in shed.values()))
    stock = {k: max(0, shed.get(k, 0)) for k in _TL_PRODUCTS}
    for i, a in enumerate(acts):
        if a and a[0] == "DROP" and pos[i] in _TL_SHED:
            for k, v in ((invs[i] if i < len(invs) else {}) or {}).items():
                v = int(v or 0)
                if k in _TL_PRODUCTS and v > 0 and room > 0:
                    t = min(v, room); stock[k] = stock.get(k, 0) + t; room -= t
    market = [list(o) if isinstance(o, (list, tuple)) else o for o in (action.get("market") or [])]
    if step >= 718:
        sells = [["SELL", k, q] for k, q in stock.items() if q > 0]
        sells.sort(key=lambda o: -int(prices.get(o[1], 0) or 0) * o[2])
        market = sells[:10]; changed = True; _TL_STATS["final_turns"] += 1
    elif _TL["spread"] and step >= int(_TL["sell_from"]):
        planned = {}
        for o in market:
            if isinstance(o, list) and len(o) >= 3 and o[0] == "SELL":
                planned[o[1]] = planned.get(o[1], 0) + int(o[2])
        add = []
        for k, q in stock.items():
            want = -(-q // (left + 1)) - planned.get(k, 0)
            if want > 0:
                add.append(["SELL", k, want])
        add.sort(key=lambda o: -int(prices.get(o[1], 0) or 0) * o[2])
        free = max(0, 10 - len(market))
        if add and free:
            market = market + add[:free]; changed = True; _TL_STATS["sell_turns"] += 1
    if not changed:
        return action
    return {"farmer": acts[0], "hands": acts[1:len(pos)], "market": market}


_TL_PARENT = agent
del agent


def agent(obs, config=None):
    action = _TL_PARENT(obs, config)
    if not _TL["on"]:
        return action
    try:
        return _tl_apply(obs, action)
    except Exception:
        _TL_STATS["errors"] += 1
        return action

agent.telemetry = _TL_STATS
