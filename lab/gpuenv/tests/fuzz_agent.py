"""Random-legal(ish) agent that hammers every op, for differential testing.

Deliberately produces plenty of *rejected* actions too (wrong tile, empty
inventory, over-capacity drops, malformed argument lists), because the silent
no-op paths are exactly where a reimplementation drifts.
"""

from __future__ import annotations

import random

CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMALS = ["GOOSE", "COW", "SHEEP"]
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK",
            "WOOL", "FERTILIZER"]
ITEMS = PRODUCTS + ANIMALS
MOVES = ["NORTH", "SOUTH", "EAST", "WEST"]


def _unit_action(rng):
    r = rng.random()
    if r < 0.30:
        return [rng.choice(MOVES)]
    if r < 0.34:
        return ["PASS"]
    if r < 0.42:
        return ["PLANT", rng.choice(CROPS)]
    if r < 0.52:
        return ["WATER"]
    if r < 0.62:
        return ["HARVEST"]
    if r < 0.65:
        return ["FERTILIZE"]
    if r < 0.68:
        return ["DIG"]
    if r < 0.71:
        return ["BUILD_COOP"]
    if r < 0.74:
        return ["BUILD_PASTURE"]
    if r < 0.80:
        return ["PLACE", rng.choice(ITEMS), rng.randint(1, 40)]
    if r < 0.83:
        return ["PLACE", rng.choice(ANIMALS)]
    if r < 0.88:
        return ["FEED"]
    if r < 0.91:
        return ["CARE"]
    if r < 0.94:
        return ["COLLECT_FERTILIZER"]
    if r < 0.98:
        return ["PICKUP", rng.choice(ITEMS), rng.randint(1, 30)]
    return ["DROP"]


def _market_order(rng, money):
    r = rng.random()
    if r < 0.12:
        return ["HIRE"]
    if r < 0.16:
        return ["BUY_LAND"]
    if r < 0.40:
        return ["BUY_SEED", rng.choice(CROPS), rng.randint(1, 4)]
    if r < 0.52:
        return ["BUY_ANIMAL", rng.choice(ANIMALS), rng.randint(1, 2)]
    if r < 0.62:
        return ["BUY_PRODUCT", rng.choice(["WHEAT", "FERTILIZER"]), rng.randint(1, 25)]
    if r < 0.66:
        return ["SELL", rng.choice(PRODUCTS), 0]          # rejected by _parse_order
    return ["SELL", rng.choice(PRODUCTS), rng.randint(1, 80)]


def make_fuzz_agent(seed: int, aggression: float = 1.0):
    rng = random.Random(seed)

    def agent(obs):
        player = obs.get("player", 0)
        farms = obs.get("farms", [])
        if not farms or player >= len(farms):
            return {"farmer": ["PASS"], "hands": [], "market": []}
        farm = farms[player]
        n_hands = len(farm.get("hands", []))
        market = [_market_order(rng, farm["money"])
                  for _ in range(rng.randint(0, int(5 * aggression)))]
        farmer = _unit_action(rng)
        hands = [_unit_action(rng) for _ in range(n_hands)]
        # occasionally emit an action for a hand that does not exist
        if rng.random() < 0.05:
            hands.append(_unit_action(rng))
        return {"farmer": farmer, "hands": hands, "market": market}

    return agent


def agent(obs):                      # module-level default (seeded per process)
    return make_fuzz_agent(0)(obs)


def make_chaos_agent(base, seed: int, p_unit: float = 0.15, p_mkt: float = 0.25):
    """Wrap a real agent and randomly corrupt/extend its action each turn.

    Keeps the economy alive (so late-game state is reached) while still hitting
    the rejected-action and edge-case paths.
    """
    rng = random.Random(seed)

    def agent(obs):
        try:
            a = base(obs)
        except Exception:
            a = {"farmer": ["PASS"], "hands": [], "market": []}
        if not isinstance(a, dict):
            a = {"farmer": ["PASS"], "hands": [], "market": []}
        farmer = a.get("farmer", ["PASS"])
        hands = list(a.get("hands", []) or [])
        market = list(a.get("market", []) or [])
        if rng.random() < p_unit:
            farmer = _unit_action(rng)
        for i in range(len(hands)):
            if rng.random() < p_unit:
                hands[i] = _unit_action(rng)
        if rng.random() < p_mkt:
            pos = rng.randint(0, len(market))
            market.insert(pos, _market_order(rng, obs["farms"][obs["player"]]["money"]))
        return {"farmer": farmer, "hands": hands, "market": market}

    return agent
