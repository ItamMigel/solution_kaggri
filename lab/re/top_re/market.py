"""top-RE market layer: HIRE / BUY_LAND / BUY_SEED / BUY_ANIMAL / BUY_PRODUCT WHEAT / SELL, max 10 orders per turn.
orders(obs, player, want, tg) -> list of market orders. Cash priority: land > hires > animals > seeds > feed; sales first."""
SEED = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
LAND = [1000, 2000, 4000]
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
STEEP = {"STRAWBERRY", "MELON", "MILK", "WOOL"}  # price falls fast with supply: meter these out
def fib_cost(n):  # cost of the (n+1)-th hire today
    a, b = 1, 1
    for _ in range(n): a, b = b, a + b
    return a
def orders(obs, player, want, tg):
    farm = obs["farms"][player]; priv = obs.get("private") or {}; shed = dict(priv.get("shed") or {}); seeds = dict(priv.get("seeds") or {})
    step = int(obs.get("step", 0)); day = int(obs["day"]); hour = int(obs.get("hour", step % 24)); money = float(farm["money"])
    prices = obs["market"]["prices"]; out = []
    carried = {}
    for inv in priv.get("inventories") or []:
        for k, v in inv.items(): carried[k] = carried.get(k, 0) + v
    animals = 0; empty_struct = {"COOP": 0, "PASTURE": 0}; tiles = farm["tiles"]
    for row in tiles:
        for t in row:
            if isinstance(t, dict) and t.get("kind") in ("COOP", "PASTURE"):
                if t.get("animal"): animals += 1
                else: empty_struct[t["kind"]] += 1
    last = step >= 715
    # --- SELL (revenue first). Keep feed wheat; meter steep items unless late game.
    planned_animals = sum(1 for r in want.values() if ":" in r)
    feed_need = max(animals, min(planned_animals, animals + 3)) * tg["wheat_reserve_per_animal"]
    for item in ("MELON", "STRAWBERRY", "MILK", "WOOL", "EGG", "CARROT", "TOMATO", "WHEAT", "FERTILIZER"):
        have = shed.get(item, 0)
        if item == "WHEAT": have -= feed_need
        if item == "FERTILIZER": have -= (25 if day >= 10 else 2)   # keep fertilizer for FERTILIZE from d10 (DSM from d11); sell before for cash
        if have <= 0 or len(out) >= 6: continue
        if item in STEEP and not last and day < 28:
            if prices[item] < 0.4 * BASE[item] and have < 25: continue   # deep glut: wait for town consumption
            have = min(have, 15)
        out.append(["SELL", item, int(have)]); money += have * prices[item] * 0.9
    # --- LAND
    nq = len(farm.get("unlocked_quadrants") or ["NW"])
    if nq < 3:
        nxt = nq + 1; st = tg["land_step"].get(nxt)
        if st is not None and step >= st and money >= LAND[nq - 1] + 150:
            out.append(["BUY_LAND"]); money -= LAND[nq - 1]
    # --- HIRE up to today's target
    need_h = tg["hands"] - len(farm.get("hands") or [])
    h = int(farm.get("hires_today", 0))
    while need_h > 0 and len(out) < 10 and money >= fib_cost(h) + 50:
        out.append(["HIRE"]); money -= fib_cost(h); h += 1; need_h -= 1
    # --- SEEDS for empty desired crop tiles
    need_s = {}
    for (x, y), role in want.items():
        if ":" in role: continue
        if tiles[y][x] is None: need_s[role] = need_s.get(role, 0) + 1
    for c in ("MELON", "WHEAT", "STRAWBERRY", "CARROT", "TOMATO"):
        n = need_s.get(c, 0) - seeds.get(c, 0)
        if n > 0 and len(out) < 10:
            k = min(n, int(max(0, money - 30) // SEED[c]))
            if k > 0: out.append(["BUY_SEED", c, k]); money -= k * SEED[c]
    # --- ANIMALS for empty structures (+ planned structure tiles still empty ground)
    need_a = {"GOOSE": 0, "COW": 0, "SHEEP": 0}
    for (x, y), role in want.items():
        if ":" not in role: continue
        kind, a = role.split(":"); t = tiles[y][x]
        if t is None or (isinstance(t, dict) and t.get("kind") == kind and not t.get("animal")): need_a[a] += 1
    for a in ("COW", "SHEEP", "GOOSE"):
        n = need_a[a] - shed.get(a, 0) - carried.get(a, 0)
        if shed.get(a, 0) + carried.get(a, 0) >= 2: n = 0   # animals waiting for placement: don't buy more
        while n > 0 and money >= ANIMAL[a] + 100 and len(out) < 10:
            k = min(n, int((money - 100) // ANIMAL[a]))
            if k <= 0: break
            out.append(["BUY_ANIMAL", a, k]); money -= k * ANIMAL[a]; n -= k
    # --- FEED wheat top-up
    wheat = shed.get("WHEAT", 0) + carried.get("WHEAT", 0)
    if wheat < feed_need and len(out) < 10:
        k = min(feed_need - wheat, int(max(0, money - 30) // max(1, prices["WHEAT"] + 1)))
        if k > 0: out.append(["BUY_PRODUCT", "WHEAT", k])
    return out[:10]
