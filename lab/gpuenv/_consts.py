"""Numeric game constants, transcribed 1:1 from the ground-truth interpreter.

Source: /venv/main/lib/python3.12/site-packages/kaggle_environments/envs/
        kaggriculture/kaggriculture.py
"""

from __future__ import annotations

from . import ops

# --------------------------------------------------------------------------- #
# Configuration defaults (kaggriculture.json)
# --------------------------------------------------------------------------- #
EPISODE_STEPS = 720
BOARD_SIZE = 10
STARTING_MONEY = 3000
MAX_MARKET_ORDERS = 10
TURNS_PER_DAY = 24
SHED_CAPACITY = 100
WEED_SPAWN_CHANCE = 0.005
TOWN_SHOP_UNLOCK_INTERVAL = 3
TOWN_SHOP_SELL_INTERVAL = 4
TOWN_CENTER_SELL_INTERVAL = 24
FARM_HAND_COST_MULT = 1

N_TILES = BOARD_SIZE * BOARD_SIZE
HALF = BOARD_SIZE // 2
# Last step on which the interpreter does any work (env.done fires afterwards).
LAST_STEP = EPISODE_STEPS - 2                     # 718
N_STEPS = LAST_STEP + 1                           # 719 interpreter calls
N_DAYS = EPISODE_STEPS // TURNS_PER_DAY           # 30

# --------------------------------------------------------------------------- #
# Crops -- indexed by item id 0..4 (WHEAT, CARROT, TOMATO, STRAWBERRY, MELON)
# --------------------------------------------------------------------------- #
CROP_SEED_COST = [10, 20, 50, 100, 80]
CROP_FIRST_YIELD_DAY = [2, 2, 8, 10, 10]
CROP_MAX_YIELD_DAY = [4, 3, 8, 10, 12]
CROP_INTERVAL = [0, 0, 1, 2, 0]
CROP_MAX_YIELD = [6, 4, 4, 4, 6]
CROP_ONGOING = [0, 0, 1, 1, 0]
# WATER bonus window: (max_yield_day + 1) // 2 <= age <= max_yield_day
CROP_WATER_WINDOW_START = [(m + 1) // 2 for m in CROP_MAX_YIELD_DAY]

# --------------------------------------------------------------------------- #
# Animals -- indexed by animal index 0..2 (GOOSE, COW, SHEEP) == item id - 9
# --------------------------------------------------------------------------- #
ANIMAL_COST = [300, 400, 500]
ANIMAL_STRUCTURE = [ops.TILE_COOP, ops.TILE_PASTURE, ops.TILE_PASTURE]
ANIMAL_FIRST_YIELD_DAY = [4, 8, 6]
ANIMAL_INTERVAL = [1, 2, 3]
ANIMAL_MAX_HELD = [4, 6, 6]
ANIMAL_PRODUCT = [ops.ITEM_EGG, ops.ITEM_MILK, ops.ITEM_WOOL]

# --------------------------------------------------------------------------- #
# Land
# --------------------------------------------------------------------------- #
LAND_PRICES = [1000, 2000, 4000]
# Source LAND_ORDER = ["NE", "SW", "SE"]; quadrant index below matches.
QUADRANT_NAMES = ["NW", "NE", "SW", "SE"]
LAND_ORDER_QUADRANT = [1, 2, 3]          # index into QUADRANT_NAMES


def _quadrant_of(x: int, y: int) -> int:
    return (0 if y < HALF else 2) + (0 if x < HALF else 1)


# [4, 100] boolean masks, flat tile index = y * 10 + x
QUADRANT_MASK = [
    [1 if _quadrant_of(i % BOARD_SIZE, i // BOARD_SIZE) == q else 0
     for i in range(N_TILES)]
    for q in range(4)
]

# _shed_access_tiles: NWSE order of (x, y)
SHED_ACCESS_TILES = [(HALF - 1, HALF - 1), (HALF, HALF - 1),
                     (HALF - 1, HALF), (HALF, HALF)]
SHED_ACCESS_FLAT = [y * BOARD_SIZE + x for (x, y) in SHED_ACCESS_TILES]
DEFAULT_SPAWN = SHED_ACCESS_TILES[0]     # first in NW == (4, 4)

# --------------------------------------------------------------------------- #
# Farmer moves: (dx, dy), y grows downward.  Indexed by OP_NORTH..OP_WEST - 1.
# --------------------------------------------------------------------------- #
MOVE_DX = [0, 0, 1, -1]
MOVE_DY = [-1, 1, 0, 0]

# --------------------------------------------------------------------------- #
# Town
# --------------------------------------------------------------------------- #
# Alphabetical, because _end_of_day picks with rng.choice(sorted(remaining)).
SHOP_NAMES = [
    "BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP",
    "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE",
]
N_SHOPS = len(SHOP_NAMES)

_SHOP_PRODUCTS = {
    "BAKERY":         ["EGG", "WHEAT"],
    "PIZZA_SHOP":     ["MILK", "TOMATO", "WHEAT"],
    "BRUNCH_SPOT":    ["EGG", "WHEAT", "STRAWBERRY"],
    "YARN_STORE":     ["WOOL"],
    "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"],
    "PET_CAFE":       ["CARROT"],
    "SMOOTHIE_SHOP":  ["STRAWBERRY", "MILK"],
    "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"],
}


def _shop_demand_row(shop: str) -> list[int]:
    products = _SHOP_PRODUCTS[shop]
    mult = 2 if len(products) == 1 else 1
    row = [0] * ops.N_PRODUCTS
    for name in products:
        row[ops.ITEM_ID[name]] += mult
    return row


# [N_SHOPS, N_PRODUCTS] -- units removed from market inventory per shop tick.
SHOP_DEMAND = [_shop_demand_row(s) for s in SHOP_NAMES]

# TOWN_CENTER_PRODUCTS = everything except FERTILIZER.
TOWN_CENTER_MASK = [1] * ops.N_PRODUCTS
TOWN_CENTER_MASK[ops.ITEM_FERTILIZER] = 0

# (day_threshold, multiplier), highest threshold first
TOWN_CENTER_DEMAND_SCHEDULE = [(20, 4), (10, 2), (0, 1)]


def town_center_mult(day: int) -> int:
    for threshold, m in TOWN_CENTER_DEMAND_SCHEDULE:
        if day >= threshold:
            return m
    return 1


# --------------------------------------------------------------------------- #
# Market price curve parameters
# --------------------------------------------------------------------------- #
MARKET_I0 = 10000
PRICE_FLOOR = 1

# item id -> (base, I0, T, below_func, below_target, above_func, above_target)
MARKET_PARAMS = [
    (25,  MARKET_I0, 400, "sqrt",   0.80, "log",    0.20),   # WHEAT
    (35,  MARKET_I0, 450, "hinge",  1.00, "sqrt",   0.70),   # CARROT
    (60,  MARKET_I0, 200, "hinge",  0.40, "sqrt",   0.60),   # TOMATO
    (120, MARKET_I0, 100, "sqrt",   0.70, "linear", 1.60),   # STRAWBERRY
    (250, MARKET_I0, 300, "log",    0.20, "sq",     3.60),   # MELON
    (50,  MARKET_I0, 332, "hinge",  0.40, "log",    0.20),   # EGG
    (160, MARKET_I0, 122, "sqrt",   0.60, "linear", 1.60),   # MILK
    (200, MARKET_I0, 105, "log",    0.20, "sq",     3.20),   # WOOL
    (100, MARKET_I0, 200, "linear", 0.40, "linear", 0.40),   # FERTILIZER
]

# --------------------------------------------------------------------------- #
# Hire cost: mult * fib(n_already_today), fib(0)=1, fib(1)=1, fib(2)=2, ...
# --------------------------------------------------------------------------- #
def _fib_table(n: int) -> list[int]:
    out = []
    a, b = 1, 1
    for _ in range(n):
        out.append(a)
        a, b = b, a + b
    return out


FIB = _fib_table(80)
