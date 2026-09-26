"""Minimal greedy unit controller (fallback / smoke test for plan+market). act(obs, plan) -> (farmer, hands)."""
ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]
CROPS = {"WHEAT": (2, 4, False, 6), "CARROT": (2, 3, False, 4), "TOMATO": (8, 8, True, 4), "STRAWBERRY": (10, 10, True, 4), "MELON": (10, 12, False, 6)}
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
def _step_toward(p, q):
    if p[0] < q[0]: return ["EAST"]
    if p[0] > q[0]: return ["WEST"]
    if p[1] < q[1]: return ["SOUTH"]
    if p[1] > q[1]: return ["NORTH"]
    return None
def act(obs, plan):
    p = plan["player"]; farm = obs["farms"][p]; priv = obs.get("private") or {}; day = int(obs["day"]); hour = int(obs.get("hour", 0))
    tiles = farm["tiles"]; want = plan["want"]; seeds = dict(priv.get("seeds") or {}); shed = dict(priv.get("shed") or {})
    units = [tuple(farm["farmer"])] + [tuple(h) for h in (farm.get("hands") or [])]
    invs = list(priv.get("inventories") or [])
    while len(invs) < len(units): invs.append({})
    tasks = []  # (value, (x,y), action, needs)
    for y in range(10):
        for x in range(10):
            t = tiles[y][x]; role = want.get((x, y))
            if t == "LOCKED": continue
            if t is None:
                if role and ":" not in role and seeds.get(role, 0) > 0: tasks.append((6, (x, y), ["PLANT", role], None))
                elif role and ":" in role: tasks.append((5, (x, y), ["BUILD_" + role.split(":")[0]], None))
                continue
            k = t.get("kind")
            if k == "WEED": tasks.append((2, (x, y), ["DIG"], None)); continue
            if k == "PLANT":
                fyd, myd, ongoing, mx = CROPS[t["crop"]]; age = day - t["planted_day"]
                if not t["watered_today"]: tasks.append((9 if t["consecutive_unwatered"] >= 1 else 4, (x, y), ["WATER"], None))
                if t.get("yield_units", 0) > 0 and (ongoing or age >= myd or t["yield_units"] >= mx): tasks.append((7, (x, y), ["HARVEST"], None))
                if role and role != t["crop"] and not ongoing and age >= myd and t.get("yield_units", 0) <= 0: tasks.append((1, (x, y), ["DIG"], None))
                continue
            if k in ("COOP", "PASTURE"):
                if t.get("animal"):
                    if not t.get("fed_today"): tasks.append((10 if t.get("consecutive_unfed", 0) >= 1 else 8, (x, y), ["FEED"], "WHEAT"))
                    if not t.get("cared_today"): tasks.append((3, (x, y), ["CARE"], None))
                    if t.get("yield_units", 0) > 0: tasks.append((6, (x, y), ["HARVEST"], None))
                    if t.get("fertilizer_available"): tasks.append((2, (x, y), ["COLLECT_FERTILIZER"], None))
                else:
                    a = (role or ":").split(":")[1]
                    if a: tasks.append((7, (x, y), ["PLACE", a], a))
    # zones: split owned tiles into len(units) contiguous chunks (by quadrant, then row) -> each unit prefers its zone
    owned = [(x, y) for y in range(10) for x in range(10) if tiles[y][x] != "LOCKED"]
    owned.sort(key=lambda t: (("NW", "NE", "SW", "SE").index(("N" if t[1] < 5 else "S") + ("W" if t[0] < 5 else "E")), t[1], t[0] if t[1] % 2 == 0 else -t[0]))
    nz = max(1, len(units)); zone = {t: (i * nz) // max(1, len(owned)) for i, t in enumerate(owned)}
    taken = set(); acts = []
    for i, u in enumerate(units):
        inv = invs[i]; carrying = {k: v for k, v in inv.items() if v > 0}
        prod = sum(v for k, v in carrying.items() if k in PRODUCTS and k != "WHEAT")
        best = None
        for val, pos, a, need in tasks:
            if (pos, a[0]) in taken: continue
            if need and carrying.get(need, 0) <= 0: continue
            d = abs(u[0] - pos[0]) + abs(u[1] - pos[1]); score = val / (1 + d)
            if zone.get(pos, 0) == i % nz: score *= 3.0
            if best is None or score > best[0]: best = (score, pos, a, d)
        # shed errands: drop products / fetch wheat or animals
        acc = min(ACCESS, key=lambda q: abs(u[0] - q[0]) + abs(u[1] - q[1])); dacc = abs(u[0] - acc[0]) + abs(u[1] - acc[1])
        unfed = sum(1 for _, _, a, n in tasks if n == "WHEAT")
        need_wheat = unfed > 0 and carrying.get("WHEAT", 0) <= 0 and shed.get("WHEAT", 0) > 0 and i < 1 + max(2, unfed // 3)
        need_animal = next((n for _, _, a, n in tasks if a[0] == "PLACE" and shed.get(n, 0) > 0 and carrying.get(n, 0) <= 0), None)
        errand = None
        at_shed = dacc == 0
        if at_shed and prod > 0: errand = ["DROP"]
        elif at_shed and carrying.get("WHEAT", 0) < 2 and shed.get("WHEAT", 0) >= 4 and unfed > 0:
            k = min(shed["WHEAT"], 4); errand = ["PICKUP", "WHEAT", k]; shed["WHEAT"] -= k
        elif at_shed and need_animal: errand = ["PICKUP", need_animal, 1]; shed[need_animal] -= 1
        elif prod >= 8 or (hour >= 22 and prod > 0): errand = ["DROP"]
        elif need_wheat: k = min(shed.get("WHEAT", 0), max(4, unfed)); errand = ["PICKUP", "WHEAT", k]; shed["WHEAT"] = shed.get("WHEAT", 0) - k
        elif need_animal: errand = ["PICKUP", need_animal, 1]; shed[need_animal] -= 1
        if errand:
            acts.append(errand if dacc == 0 else _step_toward(u, acc)); continue
        if best is None: acts.append(["PASS"]); continue
        _, pos, a, d = best; taken.add((pos, a[0]))
        acts.append(a if d == 0 else _step_toward(u, pos))
    return acts[0], acts[1:]
