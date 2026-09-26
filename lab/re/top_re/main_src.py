"""top-RE agent entry (bundled into a single main.py by bundle.py).
Pipeline per turn: plan.desired -> market.orders -> units.act."""
def _unit_plan(obs, player, want):
    tiles = obs["farms"][player]["tiles"]; seeds = (obs.get("private") or {}).get("seeds") or {}
    plant, build, place, dig = {}, {}, {}, {}
    for (x, y), role in want.items():
        t = tiles[y][x]
        if ":" in role:
            kind, animal = role.split(":")
            if t is None: build[(x, y)] = kind
            elif isinstance(t, dict) and t.get("kind") == kind and not t.get("animal"): place[(x, y)] = animal
            elif isinstance(t, dict) and t.get("kind") == "WEED": dig[(x, y)] = 1
        else:
            if t is None and seeds.get(role, 0) > 0: plant[(x, y)] = role
            elif isinstance(t, dict) and t.get("kind") == "WEED": dig[(x, y)] = 1
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if isinstance(t, dict) and t.get("kind") == "WEED": dig[(x, y)] = 1
    return {"plant_targets": plant, "build_targets": build, "place_targets": place, "dig_targets": dig, "load_size": 6, "player": player, "want": want}

def agent(obs, config=None):
    player = int(obs["player"])
    want = plan_desired(obs, player)
    tg = plan_targets(obs, player)
    try:
        market = market_orders(obs, player, want, tg)
    except Exception:
        market = []
    try:
        farmer, hands = units_act(obs, _unit_plan(obs, player, want))
    except Exception:
        farmer, hands = ["PASS"], [["PASS"] for _ in obs["farms"][player].get("hands") or []]
    return {"farmer": farmer, "hands": hands, "market": market}
