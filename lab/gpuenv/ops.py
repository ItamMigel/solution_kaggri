"""Op-id enumeration and name<->id maps for the batched kaggriculture env.

Plain, importable, side-effect free.  WP1's harness and WP3's policy both encode
actions with these ids.

Encoding conventions
--------------------
* A unit action is a triple ``(op_id, arg1, arg2)`` of ints.
* A market order is a triple ``(op_id, item_id, qty)``.
* **Every "item" argument uses the single ITEM id space** (``ITEM_*``, 0..11):
  crops are items 0..4, other products 5..8, animals 9..11.  So ``PLANT`` takes
  ``arg1 = ITEM_CARROT`` and ``BUY_SEED`` takes ``item_id = ITEM_CARROT`` -- there
  is no separate "crop id" or "animal id" space.
* **No unit op takes a tile argument.** ``_apply_unit_action`` reads
  ``pos = _farmer_position(farm, idx)`` and acts on the tile the unit is standing
  on; movement is directional only (one step N/S/E/W, silently rejected off-board
  or onto ``LOCKED``).  ``arg1``/``arg2`` therefore only ever carry item ids and
  quantities.
* Where the real sim allows an omitted count (``["PICKUP", "WHEAT"]`` -> 1), the
  encoder MUST write the effective default (``arg2 = 1``).
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Unit (farmer / hand) ops
# --------------------------------------------------------------------------- #
OP_PASS = 0
OP_NORTH = 1
OP_SOUTH = 2
OP_EAST = 3
OP_WEST = 4
OP_PLANT = 5                 # arg1 = item id of a crop (0..4)
OP_WATER = 6
OP_HARVEST = 7
OP_FERTILIZE = 8
OP_DIG = 9
OP_BUILD_COOP = 10
OP_BUILD_PASTURE = 11
OP_PLACE = 12                # arg1 = item id, arg2 = qty (shed-drop branch)
OP_FEED = 13
OP_CARE = 14
OP_COLLECT_FERTILIZER = 15
OP_PICKUP = 16               # arg1 = item id, arg2 = qty
OP_DROP = 17

N_UNIT_OPS = 18

UNIT_OP_NAMES = [
    "PASS", "NORTH", "SOUTH", "EAST", "WEST", "PLANT", "WATER", "HARVEST",
    "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PLACE", "FEED", "CARE",
    "COLLECT_FERTILIZER", "PICKUP", "DROP",
]
UNIT_OP_ID = {name: i for i, name in enumerate(UNIT_OP_NAMES)}

# Ops that take an item argument in arg1.
UNIT_OPS_WITH_ITEM = (OP_PLANT, OP_PLACE, OP_PICKUP)
# Ops that take a count in arg2 (defaults to 1 when the source action omits it).
UNIT_OPS_WITH_COUNT = (OP_PLACE, OP_PICKUP)

# --------------------------------------------------------------------------- #
# Market ops
# --------------------------------------------------------------------------- #
MKT_NONE = 0                 # empty / unused order slot
MKT_HIRE = 1
MKT_BUY_LAND = 2
MKT_SELL = 3                 # item = any PRODUCT (0..8), qty > 0
MKT_BUY_PRODUCT = 4          # item must be WHEAT or FERTILIZER
MKT_BUY_SEED = 5             # item must be a crop (0..4)
MKT_BUY_ANIMAL = 6           # item must be an animal (9..11)

N_MARKET_OPS = 7

MARKET_OP_NAMES = [
    "NONE", "HIRE", "BUY_LAND", "SELL", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL",
]
MARKET_OP_ID = {name: i for i, name in enumerate(MARKET_OP_NAMES)}

# --------------------------------------------------------------------------- #
# Items  (== the shed's key order: PRODUCTS + list(ANIMALS) in the source)
# --------------------------------------------------------------------------- #
ITEM_WHEAT = 0
ITEM_CARROT = 1
ITEM_TOMATO = 2
ITEM_STRAWBERRY = 3
ITEM_MELON = 4
ITEM_EGG = 5
ITEM_MILK = 6
ITEM_WOOL = 7
ITEM_FERTILIZER = 8
ITEM_GOOSE = 9
ITEM_COW = 10
ITEM_SHEEP = 11

ITEM_NAMES = [
    "WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL",
    "FERTILIZER", "GOOSE", "COW", "SHEEP",
]
ITEM_ID = {name: i for i, name in enumerate(ITEM_NAMES)}

N_ITEMS = 12          # shed slots
N_PRODUCTS = 9        # market-tradable products, item ids 0..8
N_CROPS = 5           # item ids 0..4 are also the crop ids
N_ANIMALS = 3         # item ids 9..11; animal index = item id - 9

PRODUCT_NAMES = ITEM_NAMES[:N_PRODUCTS]
CROP_NAMES = ITEM_NAMES[:N_CROPS]
ANIMAL_NAMES = ITEM_NAMES[9:12]

# --------------------------------------------------------------------------- #
# Tile kinds
# --------------------------------------------------------------------------- #
TILE_EMPTY = 0        # source: None
TILE_LOCKED = 1       # source: "LOCKED"
TILE_WEED = 2         # source: {"kind": "WEED"}
TILE_PLANT = 3        # source: {"kind": "PLANT", ...}
TILE_COOP = 4         # source: {"kind": "COOP"} with no animal
TILE_PASTURE = 5      # source: {"kind": "PASTURE"} with no animal
TILE_ANIMAL = 6       # source: {"kind": COOP|PASTURE, "animal": ...}

N_TILE_KINDS = 7
TILE_KIND_NAMES = [
    "EMPTY", "LOCKED", "WEED", "PLANT", "COOP", "PASTURE", "ANIMAL",
]

# --------------------------------------------------------------------------- #
# Shapes / limits used by the action tensors
# --------------------------------------------------------------------------- #
MAX_HANDS = 16               # hand action slots per player (unit slots = 1 + MAX_HANDS)
MAX_ORDERS = 10              # == configuration.maxMarketOrdersPerTurn default
N_PLAYERS = 2

# --------------------------------------------------------------------------- #
# Helpers: kaggle action list <-> triple
# --------------------------------------------------------------------------- #

def encode_unit_action(action) -> tuple[int, int, int]:
    """``["PICKUP", "WHEAT", 3]`` -> ``(OP_PICKUP, ITEM_WHEAT, 3)``.

    Anything the real sim treats as a silent no-op maps to ``(OP_PASS, 0, 0)``.
    """
    if not isinstance(action, (list, tuple)) or not action:
        return (OP_PASS, 0, 0)
    op = action[0]
    if op not in UNIT_OP_ID:
        return (OP_PASS, 0, 0)
    op_id = UNIT_OP_ID[op]
    arg1, arg2 = 0, 0
    if op_id in UNIT_OPS_WITH_ITEM:
        if len(action) < 2:
            # PLANT/PICKUP/PLACE with no item is a no-op in the source.
            return (OP_PASS, 0, 0)
        arg1 = ITEM_ID.get(action[1], -1)
        if arg1 < 0:
            # Unknown item name: the source no-ops (shed.get -> 0, crop not in
            # CROPS, ...).  Encode as an out-of-range item so the batched env
            # reproduces the no-op.
            arg1 = -1
    if op_id in UNIT_OPS_WITH_COUNT:
        arg2 = 1
        if len(action) >= 3:
            try:
                arg2 = int(action[2])
            except (TypeError, ValueError):
                return (OP_PASS, 0, 0)
    return (op_id, arg1, arg2)


def encode_market_order(order) -> tuple[int, int, int]:
    """``["SELL", "MELON", 120]`` -> ``(MKT_SELL, ITEM_MELON, 120)``.

    Orders the source's ``_parse_order`` rejects map to ``(MKT_NONE, 0, 0)``.
    """
    if not isinstance(order, (list, tuple)) or not order:
        return (MKT_NONE, 0, 0)
    op = order[0]
    if op == "HIRE":
        return (MKT_HIRE, 0, 0)
    if op == "BUY_LAND":
        return (MKT_BUY_LAND, 0, 0)
    if op in ("BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"):
        if len(order) < 3:
            return (MKT_NONE, 0, 0)
        try:
            n = int(order[2])
        except (TypeError, ValueError):
            return (MKT_NONE, 0, 0)
        if n <= 0:
            return (MKT_NONE, 0, 0)
        item = ITEM_ID.get(order[1], -1)
        return (MARKET_OP_ID[op], item, n)
    return (MKT_NONE, 0, 0)


def decode_unit_action(triple) -> list:
    op_id, arg1, arg2 = int(triple[0]), int(triple[1]), int(triple[2])
    name = UNIT_OP_NAMES[op_id]
    out = [name]
    if op_id in UNIT_OPS_WITH_ITEM:
        out.append(ITEM_NAMES[arg1] if 0 <= arg1 < N_ITEMS else "?")
    if op_id in UNIT_OPS_WITH_COUNT:
        out.append(arg2)
    return out


def decode_market_order(triple) -> list:
    op_id, item, qty = int(triple[0]), int(triple[1]), int(triple[2])
    if op_id == MKT_NONE:
        return []
    if op_id in (MKT_HIRE, MKT_BUY_LAND):
        return [MARKET_OP_NAMES[op_id]]
    return [MARKET_OP_NAMES[op_id],
            ITEM_NAMES[item] if 0 <= item < N_ITEMS else "?", qty]
