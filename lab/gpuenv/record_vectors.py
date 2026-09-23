"""WP1 — reference trajectory recorder for the kaggriculture fidelity gate.

Runs the REAL simulator
(`/venv/main/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py`)
and dumps, for every step, the full canonical state of BOTH players plus the integer-encoded
actions, into `artifacts/vectors/ep_<nnnnn>.npz` (+ `manifest.json`).

The canonical state schema and the op-id enumeration are specified in `src/gpuenv/spec.md`
(§13, §14, §15); this module is the executable definition of both and is imported by
`src/gpuenv/difftest.py`.

Usage
-----
    python -m src.gpuenv.record_vectors                     # full corpus (~230 episodes)
    python -m src.gpuenv.record_vectors --n 20 --workers 8  # quick subset
    python -m src.gpuenv.record_vectors --list              # show the episode plan, run nothing

Design notes
------------
* Agent nondeterminism is harmless: difftest replays the RECORDED ACTIONS, so only the
  simulator has to be deterministic (it is, given `seed` — see spec §11).
* An episode is REJECTED (not silently mangled) if any agent emits an action that cannot be
  encoded losslessly; the manifest reports the count.
* Sharp-edge coverage is measured by instrumenting the simulator's own internals
  (monkey-patched counters), so "shed overflow destruction fired" is a measurement of the
  engine, not a guess from the outside.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import traceback
from dataclasses import dataclass, field

import numpy as np

# --------------------------------------------------------------------------------------
# Enumerations — spec.md §13.  WP2's src/gpuenv/ops.py MUST match these.
# --------------------------------------------------------------------------------------

PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
ANIMALS = ["GOOSE", "COW", "SHEEP"]
CROPS = PRODUCTS[:5]
ITEMS = PRODUCTS + ANIMALS                      # 12 shed/inventory slots
ITEM_ID = {name: i for i, name in enumerate(ITEMS)}
CROP_ID = {name: i for i, name in enumerate(CROPS)}
ANIMAL_ID = {name: i for i, name in enumerate(ANIMALS)}
SHOPS = ["BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE",
         "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET"]
SHOP_BIT = {name: i for i, name in enumerate(SHOPS)}

# ---- op ids: `src/gpuenv/ops.py` (authored by WP2) is AUTHORITATIVE per CONTRACT.md. -----
# The fallback below is only used if ops.py does not exist yet; it is the enumeration
# documented in spec.md §13.  Recorded vectors carry a fingerprint of whichever ids were used,
# and difftest refuses to run against a corpus recorded with different ids.
_FALLBACK_UNIT_OP_ID = {
    "PASS": 0, "NORTH": 1, "SOUTH": 2, "EAST": 3, "WEST": 4, "PLANT": 5, "WATER": 6,
    "HARVEST": 7, "FERTILIZE": 8, "DIG": 9, "BUILD_COOP": 10, "BUILD_PASTURE": 11,
    "PLACE": 12, "FEED": 13, "CARE": 14, "COLLECT_FERTILIZER": 15, "PICKUP": 16, "DROP": 17,
}
_FALLBACK_MARKET_OP_ID = {"NONE": 0, "HIRE": 1, "BUY_LAND": 2, "SELL": 3,
                          "BUY_PRODUCT": 4, "BUY_SEED": 5, "BUY_ANIMAL": 6}

try:                                                            # pragma: no cover
    from src.gpuenv import ops as _ops
    UNIT_OP_ID = dict(_ops.UNIT_OP_ID)
    MARKET_OP_ID = dict(_ops.MARKET_OP_ID)
    OPS_SOURCE = "src.gpuenv.ops"
    if list(_ops.ITEM_NAMES) != ITEMS:
        raise SystemExit(f"ops.ITEM_NAMES {list(_ops.ITEM_NAMES)} != source order {ITEMS}")
except ImportError:
    UNIT_OP_ID = dict(_FALLBACK_UNIT_OP_ID)
    MARKET_OP_ID = dict(_FALLBACK_MARKET_OP_ID)
    OPS_SOURCE = "spec.md fallback"

N_UNIT_OPS = max(UNIT_OP_ID.values()) + 1
N_MARKET_OPS = max(MARKET_OP_ID.values()) + 1
UNIT_OP_NAME = {v: k for k, v in UNIT_OP_ID.items()}
MARKET_OP_NAME = {v: k for k, v in MARKET_OP_ID.items()}

OP_PASS = UNIT_OP_ID["PASS"]
OP_PLANT = UNIT_OP_ID["PLANT"]
OP_PICKUP = UNIT_OP_ID["PICKUP"]
OP_PLACE = UNIT_OP_ID["PLACE"]
MK_NONE = MARKET_OP_ID["NONE"]
MK_HIRE = MARKET_OP_ID["HIRE"]
MK_BUY_LAND = MARKET_OP_ID["BUY_LAND"]

#: fingerprint stored in every vector file; difftest checks it before replaying
OPS_FINGERPRINT = json.dumps({"unit": UNIT_OP_ID, "market": MARKET_OP_ID, "items": ITEMS},
                             sort_keys=True)

# tile kinds (spec §14 / ops.TILE_*): an occupied structure is its own kind, 6
K_EMPTY, K_LOCKED, K_WEED, K_PLANT, K_COOP, K_PASTURE, K_ANIMAL = 0, 1, 2, 3, 4, 5, 6
KIND_ID = {"WEED": K_WEED, "PLANT": K_PLANT, "COOP": K_COOP, "PASTURE": K_PASTURE}

MAX_HANDS = 16
MAX_UNITS = MAX_HANDS + 1
MAX_ORDERS = 10
BOARD = 10
N_TILE_FIELDS = 12
STEPS = 720                 # recorded states; 719 interpreter calls
SHED_ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]

VEC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                       "artifacts", "vectors")

CANON_KEYS = ["money", "farmer", "n_hands", "hands", "hires_today", "n_land", "shed", "seeds",
              "inv", "tiles", "mkt_inv", "mkt_price", "shops", "day", "hour", "step"]
CANON_DTYPE = {
    "money": np.int64, "farmer": np.int16, "n_hands": np.int16, "hands": np.int16,
    "hires_today": np.int16, "n_land": np.int16, "shed": np.int32, "seeds": np.int32,
    "inv": np.int32, "tiles": np.int16, "mkt_inv": np.int32, "mkt_price": np.int32,
    "shops": np.int32, "day": np.int16, "hour": np.int16, "step": np.int32,
}
# per-sample shape (without the leading batch/time axis)
CANON_SHAPE = {
    "money": (2,), "farmer": (2, 2), "n_hands": (2,), "hands": (2, MAX_HANDS, 2),
    "hires_today": (2,), "n_land": (2,), "shed": (2, len(ITEMS)), "seeds": (2, len(CROPS)),
    "inv": (2, MAX_UNITS, len(ITEMS)), "tiles": (2, BOARD, BOARD, N_TILE_FIELDS),
    "mkt_inv": (len(PRODUCTS),), "mkt_price": (len(PRODUCTS),), "shops": (),
    "day": (), "hour": (), "step": (),
}


class EncodeError(Exception):
    """An agent emitted an action that cannot be represented losslessly."""


# --------------------------------------------------------------------------------------
# State extraction (real observation  ->  canonical arrays)
# --------------------------------------------------------------------------------------

def extract_state(step_states) -> dict:
    """`step_states` = env.steps[t]; returns the canonical dict for that recorded state."""
    obs0 = step_states[0]["observation"]
    farms = obs0["farms"]
    out = {
        "money": np.zeros(2, np.int64),
        "farmer": np.zeros((2, 2), np.int16),
        "n_hands": np.zeros(2, np.int16),
        "hands": np.full((2, MAX_HANDS, 2), -1, np.int16),
        "hires_today": np.zeros(2, np.int16),
        "n_land": np.zeros(2, np.int16),
        "shed": np.zeros((2, len(ITEMS)), np.int32),
        "seeds": np.zeros((2, len(CROPS)), np.int32),
        "inv": np.zeros((2, MAX_UNITS, len(ITEMS)), np.int32),
        "tiles": np.zeros((2, BOARD, BOARD, N_TILE_FIELDS), np.int16),
    }
    for p in range(2):
        farm = farms[p]
        priv = step_states[p]["observation"]["private"]
        money = farm["money"]
        assert float(money) == int(money), f"non-integral money {money!r}"
        out["money"][p] = int(money)
        out["farmer"][p] = farm["farmer"]
        hands = farm["hands"]
        if len(hands) > MAX_HANDS:
            raise EncodeError(f"{len(hands)} hands exceeds MAX_HANDS={MAX_HANDS}")
        out["n_hands"][p] = len(hands)
        for h, pos in enumerate(hands):
            out["hands"][p, h] = pos
        out["hires_today"][p] = farm["hires_today"]
        out["n_land"][p] = len(farm["unlocked_quadrants"]) - 1
        for item, n in priv["shed"].items():
            out["shed"][p, ITEM_ID[item]] = n
        for crop, n in priv["seeds"].items():
            out["seeds"][p, CROP_ID[crop]] = n
        invs = priv["inventories"]
        if len(invs) > MAX_UNITS:
            raise EncodeError(f"{len(invs)} unit inventories exceeds MAX_UNITS={MAX_UNITS}")
        for u, inv in enumerate(invs):
            for item, n in inv.items():
                out["inv"][p, u, ITEM_ID[item]] = n
        T = out["tiles"][p]
        for y in range(BOARD):
            row = farm["tiles"][y]
            for x in range(BOARD):
                tile = row[x]
                if tile is None:
                    T[y, x] = (K_EMPTY, -1, -1, -1, 0, 0, 0, -1, -1, 0, 0, 0)
                elif tile == "LOCKED":
                    T[y, x] = (K_LOCKED, -1, -1, -1, 0, 0, 0, -1, -1, 0, 0, 0)
                else:
                    kind = KIND_ID[tile["kind"]]
                    if "animal" in tile:
                        kind = K_ANIMAL          # occupied structure is its own kind (ops.TILE_ANIMAL)
                        T[y, x] = (kind, -1, ANIMAL_ID[tile["animal"]], tile["placed_day"],
                                   int(tile["fed_today"]), tile["consecutive_unfed"],
                                   tile["yield_units"], -1, -1, int(tile["cared_today"]),
                                   int(tile["fertilizer_available"]), tile["pending_care_bonus"])
                    elif kind == K_PLANT:
                        T[y, x] = (kind, CROP_ID[tile["crop"]], -1, tile["planted_day"],
                                   int(tile["watered_today"]), tile["consecutive_unwatered"],
                                   tile["yield_units"], tile["max_lifespan_step"],
                                   tile["fertilized_until_day"], 0, 0, 0)
                    else:                      # bare WEED / COOP / PASTURE
                        T[y, x] = (kind, -1, -1, -1, 0, 0, 0, -1, -1, 0, 0, 0)
    market = obs0["market"]
    out["mkt_inv"] = np.array([market["inventory"][i] for i in PRODUCTS], np.int32)
    out["mkt_price"] = np.array([market["prices"][i] for i in PRODUCTS], np.int32)
    bits = 0
    for s in obs0["town"]["unlocked_shops"]:
        bits |= 1 << SHOP_BIT[s]
    out["shops"] = np.int32(bits)
    out["day"] = np.int16(obs0["day"])
    out["hour"] = np.int16(obs0["hour"])
    out["step"] = np.int32(obs0["step"])
    return out


# --------------------------------------------------------------------------------------
# Action codec
# --------------------------------------------------------------------------------------

def _as_int(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise EncodeError(f"non-numeric quantity {v!r}")
    iv = int(v)
    if not (-32768 <= iv <= 32767):
        raise EncodeError(f"quantity {iv} out of int16 range")
    return iv


def encode_unit_action(a, stats=None) -> tuple:
    """Raw farmer/hand action -> (op, arg1, arg2). Lossless: normalisations are proven no-ops."""
    if not isinstance(a, list) or not a:
        return (OP_PASS, 0, 0)                      # sim:299 — empty/none == PASS
    op = a[0]
    if not isinstance(op, str) or op not in UNIT_OP_ID:
        if stats is not None:
            stats["unknown_unit_op"] += 1           # falls through every branch == PASS
        return (OP_PASS, 0, 0)
    oid = UNIT_OP_ID[op]
    if oid == OP_PLANT:
        if len(a) < 2:
            return (OP_PASS, 0, 0)                  # sim:360 -> no-op, not counted in plant_demand
        if a[1] not in CROP_ID:
            if stats is not None:
                stats["unknown_crop"] += 1          # no-op either way (blocked or crop-not-in-CROPS)
            return (OP_PASS, 0, 0)
        return (OP_PLANT, CROP_ID[a[1]], 0)
    if oid in (OP_PICKUP, OP_PLACE):
        if len(a) < 2:
            return (OP_PASS, 0, 0)
        if a[1] not in ITEM_ID:
            if stats is not None:
                stats["unknown_item"] += 1          # shed.get/inv.get -> 0 -> no-op
            return (OP_PASS, 0, 0)
        n = _as_int(a[2]) if len(a) >= 3 else 1
        return (oid, ITEM_ID[a[1]], n)
    return (oid, 0, 0)


def encode_market_order(o, stats=None) -> tuple:
    """Raw market order -> (op, arg1, arg2). `_parse_order` rejects == MK_NONE (dead lane)."""
    if not isinstance(o, list) or not o:
        return (MK_NONE, 0, 0)
    op = o[0]
    if op == "HIRE":
        return (MK_HIRE, 0, 0)
    if op == "BUY_LAND":
        return (MK_BUY_LAND, 0, 0)
    if op not in MARKET_OP_ID:
        if stats is not None:
            stats["unknown_market_op"] += 1
        return (MK_NONE, 0, 0)                      # sim:623 -> None -> dead lane
    if len(o) < 3:
        return (MK_NONE, 0, 0)                      # sim:614
    n = _as_int(o[2])
    if n <= 0:
        return (MK_NONE, 0, 0)                      # sim:620
    if o[1] not in ITEM_ID:
        if stats is not None:
            stats["unknown_market_item"] += 1
        return (MK_NONE, 0, 0)                      # unsupported (op,item) -> order killed
    return (MARKET_OP_ID[op], ITEM_ID[o[1]], n)


def encode_actions(actions, stats=None):
    """actions = [action_p0, action_p1]; returns (farmer[2,3], hands[2,16,3], market[2,10,3])."""
    af = np.zeros((2, 3), np.int16)
    ah = np.zeros((2, MAX_HANDS, 3), np.int16)
    ah[..., 0] = OP_PASS
    am = np.zeros((2, MAX_ORDERS, 3), np.int16)
    am[..., 0] = MK_NONE
    for p, act in enumerate(actions):
        if not isinstance(act, dict):
            act = {}
        af[p] = encode_unit_action(act.get("farmer", ["PASS"]), stats)
        hands = act.get("hands", [])
        if not isinstance(hands, list):
            hands = []
        if len(hands) > MAX_HANDS:
            raise EncodeError(f"{len(hands)} hand actions exceeds MAX_HANDS={MAX_HANDS}")
        for h, ha in enumerate(hands):
            ah[p, h] = encode_unit_action(ha, stats)
        mkt = act.get("market", [])
        if not isinstance(mkt, list):
            mkt = []
        for i, o in enumerate(mkt[:MAX_ORDERS]):    # sim:534 truncates at maxMarketOrdersPerTurn
            am[p, i] = encode_market_order(o, stats)
        if len(mkt) > MAX_ORDERS and stats is not None:
            stats["orders_truncated"] += 1
    return af, ah, am


def decode_unit_action(triple) -> list:
    """Inverse of encode_unit_action — used by difftest's ground-truth adapter."""
    op, a1, a2 = int(triple[0]), int(triple[1]), int(triple[2])
    name = UNIT_OP_NAME[op]
    if op == OP_PLANT:
        return ["PLANT", CROPS[a1]]
    if op in (OP_PICKUP, OP_PLACE):
        return [name, ITEMS[a1], a2]
    return [name]


def decode_market_order(triple):
    op, a1, a2 = int(triple[0]), int(triple[1]), int(triple[2])
    if op == MK_NONE:
        return None
    if op in (MK_HIRE, MK_BUY_LAND):
        return [MARKET_OP_NAME[op]]
    return [MARKET_OP_NAME[op], ITEMS[a1], a2]


#: placeholder for an empty market lane — `_parse_order` returns None for it (sim:623), which is
#: exactly what an absent order does, while KEEPING the index of the orders behind it.
DEAD_LANE = ["_NONE_"]


def decode_actions(af, ah, am, n_hand_slots=MAX_HANDS):
    """Returns [action_dict_p0, action_dict_p1] for the real simulator.

    Market lanes are index-preserving: MK_NONE becomes a dead placeholder rather than being
    compacted away (compaction would silently promote later orders into the priority lane).
    """
    out = []
    for p in range(2):
        hands = [decode_unit_action(ah[p, h]) for h in range(n_hand_slots)]
        lanes = [decode_market_order(am[p, i]) for i in range(MAX_ORDERS)]
        last = max((i for i, o in enumerate(lanes) if o is not None), default=-1)
        market = [(o if o is not None else DEAD_LANE) for o in lanes[:last + 1]]
        out.append({"farmer": decode_unit_action(af[p]), "hands": hands, "market": market})
    return out


# --------------------------------------------------------------------------------------
# Instrumentation — sharp-edge evidence measured inside the engine
# --------------------------------------------------------------------------------------

def _new_stats():
    keys = ["unknown_unit_op", "unknown_crop", "unknown_item", "unknown_market_op",
            "unknown_market_item", "orders_truncated",
            "drop_destroyed", "eod_destroyed", "eod_drop_events",
            "animal_escape", "plant_dry_death", "weeds_spawned", "weed_draws",
            "cap_truncated", "first_prod_truncated", "care_banked", "care_paid", "care_burned",
            "hire_ok", "hire_fail", "land_ok", "land_fail",
            "sell_units", "sell_at_floor", "buy_product", "buy_seed", "buy_animal",
            "commit_fail", "lane_used", "lane_contested", "shed_over_cap_steps",
            "plant_block_events", "day29_lost_items", "day29_lost_yield"]
    s = {k: 0 for k in keys}
    s["lane_hist"] = [0] * MAX_ORDERS
    s["op_count"] = [0] * N_UNIT_OPS
    s["mkop_count"] = [0] * N_MARKET_OPS
    s["max_hands"] = 0
    return s


class Instrument:
    """Monkey-patches the simulator's internals to count real engine events."""

    def __init__(self, K, stats):
        self.K = K
        self.s = stats
        self._orig = {}

    def __enter__(self):
        K, s = self.K, self.s

        def wrap(name, fn):
            self._orig[name] = getattr(K, name)
            setattr(K, name, fn)

        orig_drop_inv = K._drop_inventories_to_shed

        def drop_inventories_to_shed(private, capacity):
            before = sum(sum(inv.values()) for inv in private["inventories"])
            shed_before = sum(private["shed"].values())
            orig_drop_inv(private, capacity)
            shed_after = sum(private["shed"].values())
            lost = before - (shed_after - shed_before)
            s["eod_drop_events"] += 1
            s["eod_destroyed"] += max(0, lost)
        wrap("_drop_inventories_to_shed", drop_inventories_to_shed)

        orig_apply = K._apply_unit_action

        def apply_unit_action(farm, private, idx, action, board_size, day, turns_per_day,
                              shed_capacity=100):
            if isinstance(action, list) and action and isinstance(action[0], str):
                oid = UNIT_OP_ID.get(action[0])
                if oid is not None:
                    s["op_count"][oid] += 1
                if action[0] == "DROP":
                    pos = K._farmer_position(farm, idx)
                    if pos is not None and tuple(pos) in {(4, 4), (5, 4), (4, 5), (5, 5)} \
                            and farm["tiles"][pos[1]][pos[0]] != "LOCKED":
                        inv = private["inventories"][idx] if idx < len(private["inventories"]) else {}
                        before = sum(inv.values())
                        shed_before = sum(private["shed"].values())
                        orig_apply(farm, private, idx, action, board_size, day, turns_per_day,
                                   shed_capacity)
                        gained = sum(private["shed"].values()) - shed_before
                        s["drop_destroyed"] += max(0, before - gained)
                        return
            orig_apply(farm, private, idx, action, board_size, day, turns_per_day, shed_capacity)
        wrap("_apply_unit_action", apply_unit_action)

        orig_animals = K._daily_refresh_animals

        def daily_refresh_animals(farm, day):
            pre = {}
            for y in range(len(farm["tiles"])):
                for x in range(len(farm["tiles"])):
                    t = farm["tiles"][y][x]
                    if isinstance(t, dict) and "animal" in t:
                        pre[(x, y)] = (t["animal"], t["yield_units"], t.get("pending_care_bonus", 0),
                                       t["fed_today"], t["cared_today"], t["placed_day"],
                                       t["consecutive_unfed"])
            orig_animals(farm, day)
            for (x, y), (animal, y0, bank, fed, cared, placed, cu) in pre.items():
                t = farm["tiles"][y][x]
                a = K.ANIMALS[animal]
                if not (isinstance(t, dict) and "animal" in t):
                    s["animal_escape"] += 1
                    continue
                dsf = (day + 1) - placed - a["first_yield_day"]
                if dsf >= 0 and dsf % a["interval"] == 0:
                    want = y0 + 1 + (bank if fed else 0)
                    if want > a["max_held"]:
                        s["cap_truncated"] += want - a["max_held"]
                        if dsf == 0:
                            s["first_prod_truncated"] += want - a["max_held"]
                    if fed and bank:
                        s["care_paid"] += bank
                    elif bank:
                        s["care_burned"] += bank
                if cared and fed:
                    s["care_banked"] += 1
        wrap("_daily_refresh_animals", daily_refresh_animals)

        orig_plants = K._daily_refresh_plants

        def daily_refresh_plants(farm, current_day, turns_per_day):
            pre = [(x, y) for y in range(len(farm["tiles"])) for x in range(len(farm["tiles"]))
                   if isinstance(farm["tiles"][y][x], dict)
                   and farm["tiles"][y][x].get("kind") == "PLANT"]
            orig_plants(farm, current_day, turns_per_day)
            for (x, y) in pre:
                t = farm["tiles"][y][x]
                if isinstance(t, dict) and t.get("kind") == "WEED":
                    s["plant_dry_death"] += 1
        wrap("_daily_refresh_plants", daily_refresh_plants)

        orig_weeds = K._spawn_weeds

        def spawn_weeds(farm, board_size, weed_chance, rng):
            draws = sum(1 for y in range(board_size) for x in range(board_size)
                        if farm["tiles"][y][x] is None)
            before = sum(1 for y in range(board_size) for x in range(board_size)
                         if isinstance(farm["tiles"][y][x], dict)
                         and farm["tiles"][y][x].get("kind") == "WEED")
            orig_weeds(farm, board_size, weed_chance, rng)
            after = sum(1 for y in range(board_size) for x in range(board_size)
                        if isinstance(farm["tiles"][y][x], dict)
                        and farm["tiles"][y][x].get("kind") == "WEED")
            s["weed_draws"] += draws
            s["weeds_spawned"] += after - before
        wrap("_spawn_weeds", spawn_weeds)

        orig_hire = K._do_hire

        def do_hire(farm, private, board_size, mult=1):
            n = len(farm["hands"])
            orig_hire(farm, private, board_size, mult)
            if len(farm["hands"]) > n:
                s["hire_ok"] += 1
                s["max_hands"] = max(s["max_hands"], len(farm["hands"]))
            else:
                s["hire_fail"] += 1
        wrap("_do_hire", do_hire)

        orig_land = K._do_buy_land

        def do_buy_land(farm, board_size):
            n = len(farm["unlocked_quadrants"])
            orig_land(farm, board_size)
            if len(farm["unlocked_quadrants"]) > n:
                s["land_ok"] += 1
            else:
                s["land_fail"] += 1
        wrap("_do_buy_land", do_buy_land)

        orig_commit = K._commit_unit

        def commit_unit(op, item, price, farm, private, market):
            ok = orig_commit(op, item, price, farm, private, market)
            if not ok:
                s["commit_fail"] += 1
            elif op == "SELL":
                s["sell_units"] += 1
                if price <= 1:
                    s["sell_at_floor"] += 1
            elif op == "BUY_PRODUCT":
                s["buy_product"] += 1
            elif op == "BUY_SEED":
                s["buy_seed"] += 1
            elif op == "BUY_ANIMAL":
                s["buy_animal"] += 1
            return ok
        wrap("_commit_unit", commit_unit)

        orig_market = K._process_market

        def process_market(state, env):
            queues = []
            for st in state:
                act = st.action if isinstance(st.action, dict) else {}
                m = act.get("market", []) if isinstance(act, dict) else []
                queues.append(list(m)[:MAX_ORDERS] if isinstance(m, list) else [])
            for i in range(max((len(q) for q in queues), default=0)):
                live = 0
                for q in queues:
                    if i < len(q) and K._parse_order(q[i]) is not None:
                        live += 1
                        s["lane_hist"][i] += 1
                        op = K._parse_order(q[i])["type"]
                        s["mkop_count"][MARKET_OP_ID[op]] += 1
                if live:
                    s["lane_used"] += 1
                if live == 2:
                    s["lane_contested"] += 1
            for st in state:
                priv = st.observation.private
                if sum(priv["shed"].values()) > 100:
                    s["shed_over_cap_steps"] += 1
            orig_market(state, env)
        wrap("_process_market", process_market)
        return self

    def __exit__(self, *exc):
        for name, fn in self._orig.items():
            setattr(self.K, name, fn)
        return False


# --------------------------------------------------------------------------------------
# Agents
# --------------------------------------------------------------------------------------

def _tile_of(obs, p, x, y):
    return obs["farms"][p]["tiles"][y][x]


def make_random_legal(seed: int, density: float = 1.0, hire_p: float = 0.05):
    """Random-legal agent: exercises the WHOLE action space, unlike our shipped agents.

    Mostly emits ops that the engine will accept in the unit's current situation, but
    deliberately keeps a fraction of blind/illegal ops so that rejection paths are covered.
    """
    rng = random.Random(seed)
    unit_ops = ["NORTH", "SOUTH", "EAST", "WEST", "PICKUP", "DROP", "PLANT", "WATER", "HARVEST",
                "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PLACE", "FEED",
                "COLLECT_FERTILIZER", "CARE", "PASS"]

    def unit_action(obs, p, pos):
        priv = obs["private"]
        x, y = pos
        tile = _tile_of(obs, p, x, y)
        on_shed = (x, y) in SHED_ACCESS
        if rng.random() < 0.30:                       # blind op: exercises rejection paths
            op = rng.choice(unit_ops)
        else:                                         # situation-aware op
            cand = ["NORTH", "SOUTH", "EAST", "WEST"]
            if on_shed:
                cand += ["PICKUP", "DROP", "PLACE"]
            if tile is None:
                cand += ["PLANT", "BUILD_COOP", "BUILD_PASTURE"]
            elif isinstance(tile, dict):
                if tile.get("kind") == "PLANT":
                    cand += ["WATER", "WATER", "HARVEST", "FERTILIZE"]
                elif "animal" in tile:
                    cand += ["FEED", "CARE", "COLLECT_FERTILIZER", "HARVEST"]
                else:
                    cand += ["DIG", "PLACE"]
            op = rng.choice(cand)
        if op == "PLANT":
            have = [c for c, n in priv["seeds"].items() if n > 0]
            return ["PLANT", rng.choice(have) if have and rng.random() < 0.8
                    else rng.choice(CROPS)]
        if op == "PICKUP":
            return ["PICKUP", rng.choice(ITEMS), rng.choice([1, 1, 2, 5, 10, 40])]
        if op == "PLACE":
            held = [i for i, n in priv["inventories"][0].items() if n > 0] if priv["inventories"] else []
            item = rng.choice(ITEMS)
            if isinstance(tile, dict) and tile.get("kind") in ("COOP", "PASTURE") and "animal" not in tile:
                item = "GOOSE" if tile["kind"] == "COOP" else rng.choice(["COW", "SHEEP"])
            elif held and rng.random() < 0.6:
                item = rng.choice(held)
            return ["PLACE", item, rng.choice([1, 5, 20])]
        return [op]

    def agent(obs):
        p = obs["player"]
        farm = obs["farms"][p]
        priv = obs["private"]
        farmer = unit_action(obs, p, farm["farmer"])
        hands = [unit_action(obs, p, h) for h in farm["hands"]]
        if rng.random() < 0.1:                        # padded slots (spec §4.0 quirk)
            hands.append(["PLANT", rng.choice(CROPS)])
        hands = hands[:MAX_HANDS]
        market = []
        money = farm["money"]
        if rng.random() < density * 0.5:
            shed_items = [i for i, n in priv["shed"].items() if n > 0]
            if shed_items:
                market.append(["SELL", rng.choice(shed_items), rng.choice([1, 2, 5, 20, 100])])
        if rng.random() < density * 0.4 and money >= 100:
            market.append(["BUY_SEED", rng.choice(CROPS), rng.choice([1, 1, 3])])
        if rng.random() < density * 0.15 and money >= 500:
            market.append(["BUY_ANIMAL", rng.choice(ANIMALS), 1])
        if rng.random() < density * 0.2:
            market.append(["BUY_PRODUCT", rng.choice(["WHEAT", "FERTILIZER"]), rng.choice([1, 5, 20])])
        room = MAX_HANDS - len(farm["hands"])
        if rng.random() < hire_p and room > 0:
            for _ in range(min(room, rng.choice([1, 1, 2, 3]))):
                market.append(["HIRE"])
        if rng.random() < 0.02:
            market.append(["BUY_LAND"])
        if rng.random() < 0.1:
            market.append(["SELL", rng.choice(ANIMALS), 3])      # unsupported (op,item): order dies
        rng.shuffle(market)
        return {"farmer": farmer, "hands": hands, "market": market[:MAX_ORDERS]}

    return agent


# ---- scripted sharp-edge agents ----

def sharp_shed_overflow(obs):
    """Buys past the shed cap (BUY_PRODUCT ignores it), then makes units carry stock so the
    end-of-day auto-drop and explicit DROP both destroy overflow."""
    p, priv, farm = obs["player"], obs["private"], obs["farms"][obs["player"]]
    hour, day = obs["hour"], obs["day"]
    shed = priv["shed"]
    market = []
    if sum(shed.values()) < 160 and farm["money"] > 2000:
        market.append(["BUY_PRODUCT", "WHEAT", 20])
    if day >= 3 and hour == 20 and shed.get("WHEAT", 0) > 0:
        market.append(["SELL", "WHEAT", 5])
    x, y = farm["farmer"]
    if (x, y) not in SHED_ACCESS:
        farmer = ["NORTH" if y > 4 else "SOUTH"] if y != 4 else ["WEST" if x > 4 else "EAST"]
    elif hour % 6 == 0:
        farmer = ["PICKUP", "WHEAT", 30]
    elif hour % 6 == 3:
        farmer = ["DROP"]
    else:
        farmer = ["PASS"]
    hands = []
    for h in farm["hands"]:
        hx, hy = h
        if (hx, hy) in SHED_ACCESS:
            hands.append(["PICKUP", "WHEAT", 25] if hour % 4 else ["DROP"])
        else:
            hands.append(["WEST" if hx > 4 else "EAST"])
    if hour == 1 and len(farm["hands"]) < 4:
        market.append(["HIRE"])
    return {"farmer": farmer, "hands": hands, "market": market[:MAX_ORDERS]}


def sharp_animals(obs):
    """Buys/places animals, feeds some and starves others (escape), CAREs to bank the bonus
    into a max_held truncation, and collects fertilizer."""
    p, priv, farm = obs["player"], obs["private"], obs["farms"][obs["player"]]
    hour, day = obs["hour"], obs["day"]
    shed, inv = priv["shed"], (priv["inventories"][0] if priv["inventories"] else {})
    market = []
    if day == 0 and hour < 6:
        for a in ("COW", "SHEEP", "GOOSE"):
            if farm["money"] >= 900:
                market.append(["BUY_ANIMAL", a, 1])
    if farm["money"] > 400 and shed.get("WHEAT", 0) < 20:
        market.append(["BUY_PRODUCT", "WHEAT", 4])
    if day >= 2 and shed.get("MILK", 0) + shed.get("WOOL", 0) + shed.get("EGG", 0) > 0:
        for it in ("MILK", "WOOL", "EGG", "FERTILIZER"):
            if shed.get(it, 0) > 0:
                market.append(["SELL", it, shed[it]])
    x, y = farm["farmer"]
    tile = _tile_of(obs, p, x, y)
    # build a small ring of structures on the shed-access tiles and around
    targets = [(4, 4), (5, 4), (4, 5), (5, 5), (3, 4), (4, 3)]
    farmer = ["PASS"]
    if (x, y) in SHED_ACCESS and hour < 3:
        farmer = ["PICKUP", "WHEAT", 8]
        for a in ("COW", "SHEEP", "GOOSE"):
            if shed.get(a, 0) > 0:
                farmer = ["PICKUP", a, 1]
                break
    elif tile is None and (x, y) in targets:
        farmer = ["BUILD_PASTURE"] if (x + y) % 2 == 0 else ["BUILD_COOP"]
    elif isinstance(tile, dict) and tile.get("kind") in ("COOP", "PASTURE") and "animal" not in tile:
        want = "GOOSE" if tile["kind"] == "COOP" else ("COW" if inv.get("COW", 0) else "SHEEP")
        farmer = ["PLACE", want, 1]
    elif isinstance(tile, dict) and "animal" in tile:
        if tile["yield_units"] > 0 and hour > 18:
            farmer = ["HARVEST"]
        elif tile["fertilizer_available"]:
            farmer = ["COLLECT_FERTILIZER"]
        elif not tile["fed_today"] and day % 5 != 3:       # day%5==3 -> deliberate starvation
            farmer = ["FEED"]
        elif not tile["cared_today"]:
            farmer = ["CARE"]
        else:
            farmer = ["WEST"] if x > 3 else ["EAST"]
    else:
        farmer = ["WEST"] if x > 4 else (["EAST"] if x < 4 else (["NORTH"] if y > 4 else ["SOUTH"]))
    if hour == 22 and (x, y) in SHED_ACCESS:
        farmer = ["DROP"]
    return {"farmer": farmer, "hands": [], "market": market[:MAX_ORDERS]}


def sharp_dropdestroy(obs):
    """Deliberately makes an explicit DROP destroy stock.

    Spends day 0 buying wheat (BUY_PRODUCT bypasses the shed cap), grows more wheat on the
    shed-access tile the farmer never leaves, and has the hands run a PICKUP-everything /
    DROP cycle.  Destruction happens whenever `shed_total + carried > 100` (spec §4.3).
    """
    p, priv, farm = obs["player"], obs["private"], obs["farms"][obs["player"]]
    day, hour = obs["day"], obs["hour"]
    shed, seeds = priv["shed"], priv["seeds"]
    invs = priv["inventories"]
    shed_total = sum(shed.values())
    market = []
    if farm["money"] >= 600 and shed_total + sum(sum(i.values()) for i in invs) < 190:
        market.append(["BUY_PRODUCT", "WHEAT", 15])
    if seeds.get("WHEAT", 0) == 0 and farm["money"] >= 10:
        market.append(["BUY_SEED", "WHEAT", 1])
    if hour == 0 and len(farm["hands"]) < 2:          # only 2 hands can reach (4,4); a 3rd is stuck
        market.append(["HIRE"])

    x, y = farm["farmer"]
    tile = _tile_of(obs, p, x, y)
    if (x, y) != (4, 4):
        farmer = ["NORTH" if y > 4 else ("SOUTH" if y < 4 else ("WEST" if x > 4 else "EAST"))]
    elif tile is None and seeds.get("WHEAT", 0) > 0:
        farmer = ["PLANT", "WHEAT"]
    elif isinstance(tile, dict) and tile.get("kind") == "PLANT":
        if tile["yield_units"] > 0 and day - tile["planted_day"] >= 4:
            farmer = ["HARVEST"]
        elif not tile["watered_today"]:
            farmer = ["WATER"]
        elif sum(invs[0].values()) if invs else 0:
            farmer = ["DROP"]
        else:
            farmer = ["PASS"]
    elif isinstance(tile, dict) and tile.get("kind") == "WEED":
        farmer = ["DIG"]
    else:
        farmer = ["DROP"]

    hands = []
    for h_i, (hx, hy) in enumerate(farm["hands"]):
        if (hx, hy) != (4, 4):
            hands.append(["WEST"] if hx > 4 else ["NORTH"])
            continue
        carried = sum(invs[h_i + 1].values()) if h_i + 1 < len(invs) else 0
        if carried == 0:
            hands.append(["PICKUP", "WHEAT", max(1, shed.get("WHEAT", 0))])
        else:
            hands.append(["DROP"])
    return {"farmer": farmer, "hands": hands, "market": market[:MAX_ORDERS]}


def sharp_weeds(obs):
    """Keeps the board maximally EMPTY (digs everything, buys all land) so the weed RNG draws
    the maximum number of times per day — the hardest case for RNG parity."""
    p, farm = obs["player"], obs["farms"][obs["player"]]
    market = [["BUY_LAND"]] if obs["hour"] in (0, 1, 2) else []
    x, y = farm["farmer"]
    tile = _tile_of(obs, p, x, y)
    if isinstance(tile, dict):
        farmer = ["DIG"]
    else:
        step = obs["day"] * 24 + obs["hour"]
        farmer = [["EAST", "SOUTH", "WEST", "NORTH"][step % 4]]
    hands = []
    for (hx, hy) in farm["hands"]:
        t = _tile_of(obs, p, hx, hy)
        hands.append(["DIG"] if isinstance(t, dict) else
                     [["SOUTH", "EAST", "NORTH", "WEST"][(hx + hy + obs["hour"]) % 4]])
    if obs["hour"] == 0 and len(farm["hands"]) < 6:
        market.append(["HIRE"])
    return {"farmer": farmer, "hands": hands, "market": market[:MAX_ORDERS]}


def sharp_day29(obs):
    """Hoards crops all season and dumps everything in the last hours of day 29 — exercises
    the no-end-of-day edge (anything left in unit inventories is lost)."""
    p, priv, farm = obs["player"], obs["private"], obs["farms"][obs["player"]]
    day, hour = obs["day"], obs["hour"]
    shed, seeds = priv["shed"], priv["seeds"]
    market = []
    if day < 20 and farm["money"] >= 40 and sum(seeds.values()) < 3:
        market.append(["BUY_SEED", "CARROT" if day % 2 else "WHEAT", 2])
    if day == 29 and hour >= 20:
        for it in PRODUCTS:
            if shed.get(it, 0) > 0:
                market.append(["SELL", it, shed[it]])
    x, y = farm["farmer"]
    tile = _tile_of(obs, p, x, y)
    farmer = ["PASS"]
    if tile is None and sum(seeds.values()) > 0:
        farmer = ["PLANT", "CARROT" if seeds.get("CARROT", 0) else
                  next((c for c, n in seeds.items() if n > 0), "WHEAT")]
    elif isinstance(tile, dict) and tile.get("kind") == "PLANT":
        if tile["yield_units"] > 0 and day - tile["planted_day"] >= 3:
            farmer = ["HARVEST"]
        elif not tile["watered_today"]:
            farmer = ["WATER"]
        else:
            farmer = ["EAST" if x < 4 else "WEST"]
    elif isinstance(tile, dict):
        farmer = ["DIG"]
    else:
        farmer = [["EAST", "SOUTH", "WEST", "NORTH"][(x + y) % 4]]
    if day == 29 and hour >= 18 and (x, y) in SHED_ACCESS:
        farmer = ["DROP"]
    elif day == 29 and hour >= 16 and (x, y) not in SHED_ACCESS:
        farmer = ["NORTH" if y > 4 else ("SOUTH" if y < 4 else ("WEST" if x > 4 else "EAST"))]
    return {"farmer": farmer, "hands": [], "market": market[:MAX_ORDERS]}


def sharp_lane(obs):
    """Puts a big SELL at market index 0 on even days and behind two HIREs on odd days —
    directly exercises the index priority lane against whatever the opponent does."""
    p, priv, farm = obs["player"], obs["private"], obs["farms"][obs["player"]]
    day, hour = obs["day"], obs["hour"]
    shed, seeds = priv["shed"], priv["seeds"]
    market = []
    sell = None
    for it in ("MELON", "STRAWBERRY", "WHEAT", "CARROT"):
        if shed.get(it, 0) > 0:
            sell = ["SELL", it, shed[it]]
            break
    if day % 2 == 1 and len(farm["hands"]) < 6:
        market.append(["HIRE"])
        market.append(["HIRE"])
    if sell is not None and hour in (5, 11, 17):
        market.append(sell)
    if farm["money"] >= 200 and sum(seeds.values()) == 0 and day < 18:
        market.append(["BUY_SEED", "MELON" if day % 3 == 0 else "WHEAT", 1])
    x, y = farm["farmer"]
    tile = _tile_of(obs, p, x, y)
    farmer = ["PASS"]
    if tile is None and sum(seeds.values()) > 0:
        farmer = ["PLANT", next(c for c, n in seeds.items() if n > 0)]
    elif isinstance(tile, dict) and tile.get("kind") == "PLANT":
        cd = {"WHEAT": (2, 4), "CARROT": (2, 3), "TOMATO": (8, 8), "STRAWBERRY": (10, 10),
              "MELON": (10, 12)}[tile["crop"]]
        if tile["yield_units"] > 0 and day - tile["planted_day"] >= cd[1]:
            farmer = ["HARVEST"]
        elif not tile["watered_today"]:
            farmer = ["WATER"]
        else:
            farmer = ["EAST" if x < 4 else "WEST"]
    elif isinstance(tile, dict):
        farmer = ["DIG"]
    elif (x, y) in SHED_ACCESS and hour == 23:
        farmer = ["DROP"]
    else:
        farmer = ["NORTH" if y > 0 and (x + y) % 3 == 0 else "EAST" if x < 4 else "WEST"]
    hands = [["DROP"] if (hx, hy) in SHED_ACCESS else ["WEST" if hx > 4 else "EAST"]
             for (hx, hy) in farm["hands"]]
    return {"farmer": farmer, "hands": hands, "market": market[:MAX_ORDERS]}


def sharp_plantblock(obs):
    """Every unit asks to PLANT the same crop while holding at most a couple of seeds —
    triggers the atomic PLANT block (spec §4.0) constantly."""
    p, priv, farm = obs["player"], obs["private"], obs["farms"][obs["player"]]
    market = []
    if farm["money"] >= 20 and sum(priv["seeds"].values()) < 2:
        market.append(["BUY_SEED", "CARROT", 1])
    if len(farm["hands"]) < 5 and obs["hour"] in (0, 1):
        market.append(["HIRE"])
    for it in PRODUCTS:
        if priv["shed"].get(it, 0) > 0:
            market.append(["SELL", it, priv["shed"][it]])
    crop = "CARROT"
    farmer = ["PLANT", crop]
    hands = [["PLANT", crop] for _ in farm["hands"]] + [["PLANT", crop]]
    x, y = farm["farmer"]
    tile = _tile_of(obs, p, x, y)
    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        farmer = ["WATER"] if not tile["watered_today"] else (
            ["HARVEST"] if tile["yield_units"] > 0 and obs["day"] - tile["planted_day"] >= 3
            else ["EAST" if x < 4 else "WEST"])
    elif isinstance(tile, dict):
        farmer = ["DIG"]
    return {"farmer": farmer, "hands": hands[:MAX_HANDS], "market": market[:MAX_ORDERS]}


AG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                      "artifacts", "agents")

BUILTIN_AGENTS = {
    "starter": "starter",
    "random_builtin": "random",
    "pass": "pass",
}
FILE_AGENTS = {
    "exp017": os.path.join(AG_DIR, "best_exp017.py"),
    "exp018": os.path.join(AG_DIR, "best_exp018.py"),
    "exp021": os.path.join(AG_DIR, "best_exp021.py"),
    "exp022": os.path.join(AG_DIR, "best_exp022.py"),
    "cand_a1": os.path.join(AG_DIR, "cand_a1.py"),
    "cand_a2": os.path.join(AG_DIR, "cand_a2.py"),
    "exp019": os.path.join(AG_DIR, "best_exp019.py"),
    "cand_b1": os.path.join(AG_DIR, "cand_b1.py"),
    "x_hyb": os.path.join(AG_DIR, "pool", "x_hyb.py"),
}
SCRIPTED_AGENTS = {
    "sharp_shed": sharp_shed_overflow,
    "sharp_dropdestroy": sharp_dropdestroy,
    "sharp_animals": sharp_animals,
    "sharp_weeds": sharp_weeds,
    "sharp_day29": sharp_day29,
    "sharp_lane": sharp_lane,
    "sharp_plantblock": sharp_plantblock,
}


def resolve_agent(name: str, seed: int):
    if name in BUILTIN_AGENTS:
        return BUILTIN_AGENTS[name]
    if name in FILE_AGENTS:
        return FILE_AGENTS[name]
    if name in SCRIPTED_AGENTS:
        return SCRIPTED_AGENTS[name]
    if name.startswith("rndlegal"):
        # rndlegal / rndlegal_dense / rndlegal_hire
        density = 1.5 if "dense" in name else 1.0
        hire_p = 0.25 if "hire" in name else 0.05
        return make_random_legal(seed * 7919 + len(name), density, hire_p)
    raise KeyError(name)


# --------------------------------------------------------------------------------------
# Episode plan
# --------------------------------------------------------------------------------------

def build_plan(limit: int | None = None):
    """(seed, agent0, agent1) triples. Base seed block 900000 to avoid colliding with
    the arena/eval seed blocks (60000-64000)."""
    pairs = []
    base = 900000

    ours = ["exp017", "exp018", "exp021", "exp022", "cand_a2", "cand_b1", "x_hyb"]
    sharps = list(SCRIPTED_AGENTS)
    rnds = ["rndlegal", "rndlegal_dense", "rndlegal_hire"]

    # 1. our agents vs each other and vs starter  (realistic, high-value trajectories)
    for rep in range(2):
        for i, a in enumerate(ours):
            pairs.append((a, "starter"))
            pairs.append((a, ours[(i + 1 + rep) % len(ours)]))
            pairs.append((a, ours[(i + 3 + rep) % len(ours)]))
    # 2. random-legal everywhere — the only source of full action-space coverage
    for r in rnds:
        for opp in ours + ["starter", "random_builtin", "pass"] + rnds:
            pairs.append((r, opp))
            pairs.append((opp, r))
    # 3. sharp edges vs everything interesting
    for sname in sharps:
        for opp in ["starter", "rndlegal", "cand_b1", "x_hyb"] + sharps:
            pairs.append((sname, opp))
        for opp in ["rndlegal_hire", "exp022", "sharp_weeds", "sharp_animals"]:
            pairs.append((opp, sname))
    # 4. the lane test needs mirrored lane usage on both sides
    pairs += [("sharp_lane", "sharp_lane")] * 3
    pairs += [("sharp_shed", "sharp_shed")] * 2
    pairs += [("sharp_animals", "sharp_animals")] * 2

    plan = [(base + i, a, b) for i, (a, b) in enumerate(pairs)]
    if limit:
        # keep the mix representative rather than truncating one family
        step = max(1, len(plan) // limit)
        plan = plan[::step][:limit]
    return plan


# --------------------------------------------------------------------------------------
# Recording
# --------------------------------------------------------------------------------------

def record_episode(seed: int, name0: str, name1: str, out_dir: str, ep_id: int):
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as K

    stats = _new_stats()
    t0 = time.time()
    with Instrument(K, stats):
        env = make("kaggriculture", configuration={"episodeSteps": STEPS, "seed": seed}, debug=False)
        env.run([resolve_agent(name0, seed), resolve_agent(name1, seed + 1)])
    steps = env.steps
    if len(steps) != STEPS:
        raise EncodeError(f"episode produced {len(steps)} recorded states, expected {STEPS}")

    T = len(steps)
    A = T - 1
    canon = {k: np.zeros((T,) + CANON_SHAPE[k], CANON_DTYPE[k]) for k in CANON_KEYS}
    a_farmer = np.zeros((A, 2, 3), np.int16)
    a_hands = np.zeros((A, 2, MAX_HANDS, 3), np.int16)
    a_market = np.zeros((A, 2, MAX_ORDERS, 3), np.int16)

    prev = None
    for t in range(T):
        st = extract_state(steps[t])
        for k in CANON_KEYS:
            canon[k][t] = st[k]
        if t > 0:
            raw = [steps[t][i].get("action") for i in range(2)]
            af, ah, am = encode_actions(raw, stats)
            a_farmer[t - 1] = af
            a_hands[t - 1] = ah
            a_market[t - 1] = am
            # atomic PLANT block detection needs the PRE-action seed counts
            for p in range(2):
                demand = {}
                for trip in [af[p]] + [ah[p, h] for h in range(MAX_HANDS)]:
                    if trip[0] == OP_PLANT:
                        demand[int(trip[1])] = demand.get(int(trip[1]), 0) + 1
                for c, n in demand.items():
                    if n > prev["seeds"][p, c]:
                        stats["plant_block_events"] += 1
        prev = st

    last = canon
    stats["max_hands"] = int(max(stats["max_hands"], canon["n_hands"].max()))
    stats["day29_lost_items"] = int(last["inv"][-1].sum())
    stats["day29_lost_yield"] = int(np.clip(last["tiles"][-1][..., 6], 0, None).sum())
    stats["final_money"] = [int(v) for v in last["money"][-1]]
    stats["wall_s"] = round(time.time() - t0, 2)

    path = os.path.join(out_dir, f"ep_{ep_id:05d}.npz")
    np.savez_compressed(
        path,
        seed=np.int64(seed),
        agents=np.array([name0, name1]),
        ops_fp=np.array([OPS_FINGERPRINT]),
        a_farmer=a_farmer, a_hands=a_hands, a_market=a_market,
        flags=np.array([json.dumps(stats)]),
        **canon,
    )
    return path, stats


# --------------------------------------------------------------------------------------
# Crash detection  (spec §10)
#
# The terminal `status` and `reward` are USELESS for this: `sim:928-931` unconditionally
# rewrites BOTH on the final interpreter call, so an agent that raised at step 100 finishes
# the episode with `status="DONE"` and `reward=<its money>`.  Anything keying on
# `reward is None` (src/arena.py:38-40, src/eval_lb.py:107-118) is a vacuous check.
#
# Three channels DO survive.  Verified against deliberately broken agents:
#
#   channel                          raise@0  raise@100  raise@718  timeout  malformed  clean
#   ------------------------------   -------  ---------  ---------  -------  ---------  -----
#   log[p]["stderr"] has a Traceback   YES       YES        YES        no        no       no
#   agent stops being called           YES       YES        no         YES       no       no
#   per-step status ERROR/TIMEOUT      YES       YES        no         YES       no       no
#   terminal status / reward           no        no         no         no        no       no
#
# So: `stderr` is the only channel that catches a crash on the FINAL step (the interpreter
# rewrites status there); "stopped being called" is the only channel with no false-positive
# risk at all.  Use the OR of the two.
#
# A malformed / schema-violating return value is NOT an error anywhere: `process_schema`
# silently substitutes the default action `{"farmer":["PASS"],"hands":[],"market":[]}` and
# the agent keeps playing.  It is undetectable from the record and costs only that turn.
# --------------------------------------------------------------------------------------

_TB_MARK = "Traceback (most recent call last)"


def detect_crashes(env):
    """Per-player crash report for a FINISHED episode. Returns a list of dicts, one per player.

    Keys: crashed (bool), kind, first_step, n_agent_calls, n_interp_calls, statuses,
          max_duration_s, stderr_tail.
    """
    S, L = env.steps, env.logs
    n_calls = len(S) - 1                       # interpreter calls == agent decisions (719)
    off = len(L) - n_calls                     # logs carries reset() rows in front of step rows
    out = []
    for p in range(len(S[0])):
        called, tb_steps, max_dur, tail = [], [], 0.0, None
        for k in range(n_calls):
            j = off + k
            row = L[j] if 0 <= j < len(L) else []
            lg = row[p] if p < len(row) and isinstance(row[p], dict) else {}
            if "duration" in lg:
                called.append(k)
                max_dur = max(max_dur, float(lg["duration"]))
            err = lg.get("stderr") or ""
            if _TB_MARK in err:
                tb_steps.append(k)
                if tail is None:
                    tail = err.strip().splitlines()[-1][:200]
        statuses = sorted({S[t][p]["status"] for t in range(1, len(S))}
                          - {"ACTIVE", "DONE", "INACTIVE"})
        stopped = len(called) < n_calls
        crashed = bool(tb_steps) or stopped
        if not crashed:
            kind = "clean"
        elif "TIMEOUT" in statuses:
            kind = "timeout"
        elif tb_steps and not stopped:
            kind = "exception_on_final_step"    # invisible in status; only stderr sees it
        elif tb_steps or "ERROR" in statuses:
            kind = "exception"
        elif "INVALID" in statuses:
            kind = "invalid_action"
        else:
            kind = "stopped_being_called"
        first = tb_steps[0] if tb_steps else (called[-1] + 1 if called else 0)
        out.append({"crashed": crashed, "kind": kind,
                    "first_step": first if crashed else None,
                    "n_agent_calls": len(called), "n_interp_calls": n_calls,
                    "statuses": statuses, "max_duration_s": round(max_dur, 4),
                    "stderr_tail": tail})
    return out


AUDIT_AGENTS = ["cand_b1", "cand_a1", "cand_a2", "exp022", "x_hyb",
                "exp017", "exp018", "exp019", "exp021"]
AUDIT_OPPONENTS = ["starter", "cand_b1", "x_hyb", "exp022", "rndlegal"]


def _audit_worker(args):
    a, b, seed = args
    from kaggle_environments import make
    try:
        env = make("kaggriculture", configuration={"episodeSteps": STEPS, "seed": seed},
                   debug=False)
        env.run([resolve_agent(a, seed), resolve_agent(b, seed + 1)])
        rep = detect_crashes(env)
        return {"ok": True, "seed": seed, "agents": [a, b], "players": rep,
                "money": [float(env.steps[-1][i].get("reward") or 0) for i in range(2)]}
    except Exception as e:                                            # noqa: BLE001
        return {"ok": False, "seed": seed, "agents": [a, b],
                "error": f"{type(e).__name__}: {e}"}


def audit_crashes(seeds=16, seed0=770000, workers=26, agents=None, opponents=None):
    import multiprocessing as mp
    agents = agents or AUDIT_AGENTS
    opponents = opponents or AUDIT_OPPONENTS
    jobs = []
    for a in agents:
        for o in opponents:
            for i in range(seeds):
                jobs.append((a, o, seed0 + i))            # our agent as player 0
                jobs.append((o, a, seed0 + i))            # ... and as player 1
    print(f"crash audit: {len(jobs)} episodes "
          f"({len(agents)} agents x {len(opponents)} opponents x {seeds} seeds x 2 sides)",
          flush=True)
    t0 = time.time()
    with mp.get_context("spawn").Pool(workers) as pool:
        res = []
        for i, r in enumerate(pool.imap_unordered(_audit_worker, jobs, chunksize=4)):
            res.append(r)
            if (i + 1) % 200 == 0:
                print(f"  {i+1}/{len(jobs)} ({time.time()-t0:.0f}s)", flush=True)

    per = {}
    for r in res:
        if not r["ok"]:
            print(f"  HARNESS FAILURE {r['agents']} seed {r['seed']}: {r['error']}")
            continue
        for p, name in enumerate(r["agents"]):
            d = per.setdefault(name, {"episodes": 0, "crashes": 0, "kinds": {},
                                      "max_duration_s": 0.0, "examples": []})
            info = r["players"][p]
            d["episodes"] += 1
            d["max_duration_s"] = max(d["max_duration_s"], info["max_duration_s"])
            if info["crashed"]:
                d["crashes"] += 1
                d["kinds"][info["kind"]] = d["kinds"].get(info["kind"], 0) + 1
                if len(d["examples"]) < 3:
                    d["examples"].append({"seed": r["seed"], "vs": r["agents"][1 - p],
                                          "side": p, "step": info["first_step"],
                                          "kind": info["kind"], "err": info["stderr_tail"]})
    print(f"\ncrash audit complete: {len(res)} episodes in {time.time()-t0:.0f}s\n")
    print(f"{'agent':<16} {'episodes':>9} {'crashes':>8} {'rate':>7} {'max act (s)':>12}  kinds")
    print("-" * 78)
    for name in sorted(per, key=lambda n: (-per[n]["crashes"], n)):
        d = per[name]
        rate = d["crashes"] / d["episodes"] if d["episodes"] else 0.0
        print(f"{name:<16} {d['episodes']:>9} {d['crashes']:>8} {rate:>6.2%} "
              f"{d['max_duration_s']:>12.3f}  {d['kinds'] or ''}")
    for name, d in per.items():
        for ex in d["examples"]:
            print(f"  ! {name} seed={ex['seed']} vs {ex['vs']} side={ex['side']} "
                  f"step={ex['step']} {ex['kind']}: {ex['err']}")
    total = sum(d["crashes"] for d in per.values())
    print(f"\nTOTAL CRASHES: {total}")
    return per, total


def _worker(args):
    seed, name0, name1, out_dir, ep_id = args
    try:
        path, stats = record_episode(seed, name0, name1, out_dir, ep_id)
        return {"ok": True, "ep": ep_id, "seed": seed, "agents": [name0, name1],
                "file": os.path.basename(path), "stats": stats}
    except Exception as e:                                            # noqa: BLE001
        return {"ok": False, "ep": ep_id, "seed": seed, "agents": [name0, name1],
                "error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-1500:]}


AGG_INT_KEYS = None


def aggregate(records):
    agg = {}
    for r in records:
        if not r.get("ok"):
            continue
        for k, v in r["stats"].items():
            if isinstance(v, int):
                agg[k] = agg.get(k, 0) + v
            elif isinstance(v, list) and v and isinstance(v[0], int) and k in ("lane_hist", "op_count", "mkop_count"):
                cur = agg.get(k) or [0] * len(v)
                agg[k] = [a + b for a, b in zip(cur, v)]
    # episodes in which each sharp edge fired at least once
    fired = {}
    for key in ["drop_destroyed", "eod_destroyed", "animal_escape", "plant_dry_death",
                "cap_truncated", "first_prod_truncated", "care_paid", "care_burned",
                "sell_at_floor", "lane_contested", "shed_over_cap_steps", "plant_block_events",
                "day29_lost_items", "day29_lost_yield", "land_ok", "hire_fail", "buy_product",
                "buy_animal", "weeds_spawned", "commit_fail"]:
        fired[key] = sum(1 for r in records if r.get("ok") and r["stats"].get(key, 0) > 0)
    agg["_episodes_where_fired"] = fired
    agg["max_hands"] = max((r["stats"]["max_hands"] for r in records if r.get("ok")), default=0)
    return agg


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=VEC_DIR)
    ap.add_argument("--n", type=int, default=None, help="limit episodes (representative subset)")
    ap.add_argument("--workers", type=int, default=min(24, os.cpu_count() or 4))
    ap.add_argument("--list", action="store_true", help="print the plan and exit")
    ap.add_argument("--audit-crashes", action="store_true",
                    help="run the crash detector over the shipped agents instead of recording")
    ap.add_argument("--audit-seeds", type=int, default=16)
    args = ap.parse_args(argv)

    if args.audit_crashes:
        _, total = audit_crashes(seeds=args.audit_seeds, workers=args.workers)
        return 0 if total == 0 else 1

    plan = build_plan(args.n)
    if args.list:
        for i, (s, a, b) in enumerate(plan):
            print(f"{i:4d} seed={s} {a} vs {b}")
        print(f"total {len(plan)} episodes")
        return 0

    os.makedirs(args.out, exist_ok=True)
    jobs = [(s, a, b, args.out, i) for i, (s, a, b) in enumerate(plan)]
    print(f"recording {len(jobs)} episodes with {args.workers} workers -> {args.out}", flush=True)

    t0 = time.time()
    records = []
    if args.workers <= 1:
        for j in jobs:
            records.append(_worker(j))
            print(f"  {len(records)}/{len(jobs)}", flush=True)
    else:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(args.workers) as pool:
            for i, r in enumerate(pool.imap_unordered(_worker, jobs)):
                records.append(r)
                if not r["ok"]:
                    print(f"  FAILED ep {r['ep']} ({r['agents']}): {r['error']}", flush=True)
                if (i + 1) % 20 == 0:
                    print(f"  {i+1}/{len(jobs)}  ({time.time()-t0:.0f}s)", flush=True)

    ok = [r for r in records if r["ok"]]
    records.sort(key=lambda r: r["ep"])
    manifest = {
        "n_planned": len(jobs),
        "n_recorded": len(ok),
        "n_failed": len(records) - len(ok),
        "steps_per_episode": STEPS,
        "max_hands_cap": MAX_HANDS,
        "max_orders_cap": MAX_ORDERS,
        "wall_s": round(time.time() - t0, 1),
        "episodes": [{k: r[k] for k in ("ep", "seed", "agents", "file", "ok")} | (
            {"stats": r["stats"]} if r["ok"] else {"error": r["error"]}) for r in records],
        "aggregate": aggregate(records),
    }
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)

    agg = manifest["aggregate"]
    print(f"\nrecorded {len(ok)}/{len(jobs)} episodes in {manifest['wall_s']}s")
    print("sharp-edge coverage (episodes where the engine event fired at least once):")
    for k, v in sorted(agg["_episodes_where_fired"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:24s} {v:4d} episodes   (total {agg.get(k, 0)})")
    print(f"  max hands ever alive: {agg['max_hands']} (cap {MAX_HANDS})")
    print("unit-op usage:", {UNIT_OP_NAME[i]: n for i, n in enumerate(agg.get("op_count", []))
                             if n})
    print("market-op usage:", {MARKET_OP_NAME.get(i, "NONE"): n
                               for i, n in enumerate(agg.get("mkop_count", [])) if n})
    print("market lane histogram:", agg.get("lane_hist"))
    return 0 if len(ok) == len(jobs) else 1


if __name__ == "__main__":
    sys.exit(main())
