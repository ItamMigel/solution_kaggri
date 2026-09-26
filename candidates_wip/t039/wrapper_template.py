# T039 append-only wrapper for candidates/es7_wm/pkg/main.py.
#
# Append this file *after* the complete frozen es7_wm main.py.  `_FM_PARENT`
# then names the final callable, so this pass runs after RACE, V92 queue,
# final-day planning, and the promoted WHEAT market layer.
#
# Default is intentionally inert.  A learned advisor is allowed to return
# "hold" only for the seven steep SELL items below; every other order and all
# unit commands are passed through byte-for-byte as supplied by es7_wm.

_FM = {
    "enabled": False,
    # Do not defer a sale if the shared shed has fewer free units than this.
    # The model caller may tune this only after a separately verified build.
    "min_free_shed": 12,
}
_FM_STEEP = frozenset(("STRAWBERRY", "MILK", "WOOL", "MELON", "EGG", "CARROT", "TOMATO"))
_FM_PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON",
                "EGG", "MILK", "WOOL", "FERTILIZER")
_FM_STATS = {"calls": 0, "eligible_turns": 0, "held_turns": 0,
             "held_orders": 0, "endgame_skips": 0, "room_skips": 0,
             "advisor_errors": 0}


def flow_advisor(features, proposed_sell_quantities):
    """Return {product: "sell"|"hold"}; replace only this stub with the model.

    `features` is entirely from the current legal observation: hour/day, own
    shed stock, displayed prices/inventory, unlocked shops, and opponent public
    macro.  `proposed_sell_quantities` is the final es7_wm market plan for all
    nine product dimensions.  Returning an unknown value, product, or raising
    is conservatively treated as `sell`.
    """
    return {item: "sell" for item in _FM_STEEP}


def _fm_opponent_macro(obs, player):
    farms = obs.get("farms") or []
    rival = farms[1 - player] if len(farms) == 2 else {}
    tiles = rival.get("tiles") or []
    animals = {"COW": 0, "SHEEP": 0, "GOOSE": 0}
    for row in tiles:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal") in animals:
                animals[tile["animal"]] += 1
    return {"money": int(rival.get("money", 0)),
            "hands": len(rival.get("hands") or []),
            "quadrants": len(rival.get("unlocked_quadrants") or []),
            "animals": animals}


def _fm_features(obs, player):
    private = obs.get("private") or {}
    shed = private.get("shed") or {}
    market = obs.get("market") or {}
    return {
        "hour": int(obs.get("step", 0)) % 24,
        "day": int(obs.get("step", 0)) // 24,
        "shed_stock": {item: max(0, int(shed.get(item, 0))) for item in _FM_PRODUCTS},
        "prices": {item: float((market.get("prices") or {}).get(item, 0)) for item in _FM_PRODUCTS},
        "market_inventory": {item: int((market.get("inventory") or {}).get(item, 0)) for item in _FM_PRODUCTS},
        "shops": list((obs.get("town") or {}).get("unlocked_shops") or []),
        "opponent_macro": _fm_opponent_macro(obs, player),
    }


_FM_PARENT = agent
del agent


def agent(obs, config=None):
    action = _FM_PARENT(obs, config)
    if not _FM["enabled"]:
        return action
    try:
        _FM_STATS["calls"] += 1
        step = int(obs.get("step", 0))
        # The inherited final-day planner owns this window; never intervene.
        if step >= 696:
            _FM_STATS["endgame_skips"] += 1
            return action
        private = obs.get("private") or {}
        shed = private.get("shed") or {}
        capacity = int(private.get("shed_capacity", 100))
        free_room = max(0, capacity - sum(max(0, int(q)) for q in shed.values()))
        if free_room < int(_FM["min_free_shed"]):
            _FM_STATS["room_skips"] += 1
            return action
        market = action.get("market") or []
        proposed = {item: 0 for item in _FM_PRODUCTS}
        for order in market:
            if isinstance(order, (list, tuple)) and len(order) >= 3 and order[0] == "SELL" and order[1] in proposed:
                proposed[order[1]] += max(0, int(order[2]))
        eligible = {item for item in _FM_STEEP if proposed[item] > 0}
        if not eligible:
            return action
        _FM_STATS["eligible_turns"] += 1
        player = int(obs.get("player", 0))
        try:
            advice = flow_advisor(_fm_features(obs, player), proposed)
        except Exception:
            _FM_STATS["advisor_errors"] += 1
            return action
        if not isinstance(advice, dict):
            return action
        held = {item for item in eligible if advice.get(item) == "hold"}
        if not held:
            return action
        # The sole mutation authority: remove only approved steep SELL rows.
        # BUY/HIRE/LAND, WHEAT/FERTILIZER orders and farmer/hands are untouched.
        result = dict(action)
        result["market"] = [order for order in market
                            if not (isinstance(order, (list, tuple)) and len(order) >= 3
                                    and order[0] == "SELL" and order[1] in held)]
        _FM_STATS["held_turns"] += 1
        _FM_STATS["held_orders"] += sum(1 for order in market
                                         if isinstance(order, (list, tuple)) and len(order) >= 3
                                         and order[0] == "SELL" and order[1] in held)
        return result
    except Exception:
        # A model/schema error must fail open to the frozen es7_wm action.
        _FM_STATS["advisor_errors"] += 1
        return action


agent.telemetry = _FM_STATS
