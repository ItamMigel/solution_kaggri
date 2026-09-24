"""Observation -> tensors for behavioural cloning (numpy only; embedded verbatim into the BC agent).
board: (C, 10, 10) own farm; glob: (G,) global vector; units: list of (x, y, unit_vec).
Also the action vocabularies and encode/decode helpers."""
import numpy as np

N = 10
CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
FIRST_YIELD = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
ANIMALS = ["GOOSE", "COW", "SHEEP"]
ITEMS = PRODUCTS + ANIMALS
SHOPS = ["BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP", "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE"]
SHED_ADJ = {(4, 4), (5, 4), (4, 5), (5, 5)}
BASE_PRICE = {"WHEAT": 30, "CARROT": 45, "TOMATO": 90, "STRAWBERRY": 200, "MELON": 250, "EGG": 60, "MILK": 150, "WOOL": 200, "FERTILIZER": 100}

UNIT_OPS = (["PASS", "NORTH", "SOUTH", "EAST", "WEST", "WATER", "HARVEST", "FERTILIZE", "DROP", "DIG",
             "BUILD_COOP", "BUILD_PASTURE", "FEED", "COLLECT_FERTILIZER", "CARE"]
            + ["PLANT:" + c for c in CROPS] + ["PICKUP:" + i for i in ITEMS] + ["PLACE:" + i for i in ITEMS])
UNIT_IDX = {k: i for i, k in enumerate(UNIT_OPS)}
MKT_KEYS = (["HIRE", "BUY_LAND"] + ["SELL:" + p for p in PRODUCTS] + ["BUY_SEED:" + c for c in CROPS]
            + ["BUY_ANIMAL:" + a for a in ANIMALS] + ["BUY_PRODUCT:WHEAT", "BUY_PRODUCT:FERTILIZER"])
MKT_IDX = {k: i for i, k in enumerate(MKT_KEYS)}
MKT_MAX = 40  # quantity buckets 0..MKT_MAX (clipped)
C_BOARD = 30


def _g(d, k, default=None):
    try:
        v = d.get(k, default)
    except AttributeError:
        v = getattr(d, k, default)
    return default if v is None else v


def board_tensor(obs, p):
    farm = obs["farms"][p]; day = int(_g(obs, "day", 0))
    B = np.zeros((C_BOARD, N, N), np.float32)
    tiles = farm["tiles"]
    for y in range(N):
        for x in range(N):
            t = tiles[y][x]
            if t is None:
                B[0, y, x] = 1
            elif t == "LOCKED":
                B[1, y, x] = 1
            elif isinstance(t, dict):
                k = t.get("kind")
                if k == "WEED":
                    B[2, y, x] = 1
                elif k == "PLANT":
                    c = t.get("crop")
                    if c in CROPS:
                        B[3 + CROPS.index(c), y, x] = 1
                        age = day - int(_g(t, "planted_day", day))
                        B[8, y, x] = age / 10.0
                        B[29, y, x] = 1.0 if age >= FIRST_YIELD[c] else 0.0
                    B[9, y, x] = 1.0 if t.get("watered_today") else 0.0
                    B[10, y, x] = float(_g(t, "yield_units", 0)) / 10.0
                    B[11, y, x] = 1.0 if int(_g(t, "fertilized_until_day", -1)) >= day else 0.0
                    B[12, y, x] = float(_g(t, "consecutive_unwatered", 0))
                elif k in ("COOP", "PASTURE"):
                    B[13 if k == "COOP" else 14, y, x] = 1
                    a = t.get("animal")
                    if a in ANIMALS:
                        B[15 + ANIMALS.index(a), y, x] = 1
                        B[18, y, x] = 1.0 if t.get("fed_today") else 0.0
                        B[19, y, x] = 1.0 if t.get("cared_today") else 0.0
                        B[20, y, x] = float(_g(t, "yield_units", 0)) / 10.0
                        B[21, y, x] = float(_g(t, "fertilizer_available", 0)) / 5.0
                        B[22, y, x] = float(_g(t, "pending_care_bonus", 0)) / 5.0
                        B[23, y, x] = float(_g(t, "consecutive_unfed", 0))
    fx, fy = farm["farmer"]; B[24, fy, fx] = 1
    for h in farm.get("hands") or []:
        B[25, h[1], h[0]] += 1
    for (x, y) in SHED_ADJ:
        B[26, y, x] = 1
    B[27] = np.arange(N)[None, :] / 9.0
    B[28] = np.arange(N)[:, None] / 9.0
    return B


def glob_vec(obs, p):
    farm = obs["farms"][p]; opp = obs["farms"][1 - p]; m = obs["market"]; priv = obs.get("private") or {}
    step = int(_g(obs, "step", 0))
    v = [step / 719.0, int(_g(obs, "hour", step % 24)) / 23.0, int(_g(obs, "day", step // 24)) / 29.0,
         float(farm["money"]) / 5e4, float(opp["money"]) / 5e4, np.log1p(max(0.0, float(farm["money"]))) / 12.0]
    pr = m.get("prices") or {}; inv = m.get("inventory") or {}
    v += [float(pr.get(i, 0)) / BASE_PRICE[i] for i in PRODUCTS]
    v += [(10000.0 - float(inv.get(i, 10000))) / 500.0 for i in PRODUCTS]
    shed = priv.get("shed") or {}; seeds = priv.get("seeds") or {}
    v += [float(shed.get(i, 0)) / 50.0 for i in ITEMS]
    v += [float(seeds.get(c, 0)) / 20.0 for c in CROPS]
    v += [float(_g(farm, "hires_today", 0)) / 15.0, len(farm.get("hands") or []) / 15.0,
          len(_g(farm, "unlocked_quadrants", [])) / 4.0, len(opp.get("hands") or []) / 15.0]
    shops = list((_g(obs, "town", {}) or {}).get("unlocked_shops") or [])
    v += [shops.count(s) / 2.0 for s in SHOPS]
    v += [1.0 if shops[:2].count("YARN_STORE") else 0.0]
    for f in (farm, opp):
        cnt = {a: 0 for a in ANIMALS}; plants = {c: 0 for c in CROPS}
        for row in f["tiles"]:
            for t in row:
                if isinstance(t, dict):
                    if t.get("animal") in cnt: cnt[t["animal"]] += 1
                    if t.get("kind") == "PLANT" and t.get("crop") in plants: plants[t["crop"]] += 1
        v += [cnt[a] / 10.0 for a in ANIMALS] + [plants[c] / 20.0 for c in CROPS]
    return np.asarray(v, np.float32)


def unit_list(obs, p):
    farm = obs["farms"][p]; priv = obs.get("private") or {}
    invs = priv.get("inventories") or []
    pos = [farm["farmer"]] + list(farm.get("hands") or [])
    out = []
    for i, (x, y) in enumerate(pos):
        inv = invs[i] if i < len(invs) else {}
        u = [1.0 if i == 0 else 0.0, x / 9.0, y / 9.0, 1.0 if (x, y) in SHED_ADJ else 0.0]
        u += [float((inv or {}).get(it, 0)) / 10.0 for it in ITEMS]
        u += [sum((inv or {}).values()) / 20.0 if inv else 0.0]
        out.append((int(x), int(y), np.asarray(u, np.float32)))
    return out


G_DIM = 6 + 9 + 9 + 12 + 5 + 4 + 8 + 1 + 16
U_DIM = 4 + 12 + 1


def encode_unit_action(a):
    if not a:
        return UNIT_IDX["PASS"]
    op = a[0]
    if op in ("PLANT", "PICKUP", "PLACE") and len(a) > 1:
        return UNIT_IDX.get(op + ":" + str(a[1]), UNIT_IDX["PASS"])
    return UNIT_IDX.get(op, UNIT_IDX["PASS"])


def encode_market(orders):
    q = np.zeros(len(MKT_KEYS), np.int64)
    for o in orders or []:
        if not isinstance(o, list) or not o:
            continue
        key = o[0] if o[0] in ("HIRE", "BUY_LAND") else o[0] + ":" + str(o[1]) if len(o) > 1 else o[0]
        if key in MKT_IDX:
            q[MKT_IDX[key]] += int(o[2]) if len(o) > 2 and o[0] not in ("HIRE", "BUY_LAND") else 1
    return np.minimum(q, MKT_MAX)


MKT_ORDER = (["SELL:" + p for p in PRODUCTS] + ["HIRE"] + ["BUY_ANIMAL:" + a for a in ANIMALS]
             + ["BUY_SEED:" + c for c in CROPS] + ["BUY_PRODUCT:WHEAT", "BUY_PRODUCT:FERTILIZER", "BUY_LAND"])


def decode_market(q):
    orders = []
    for key in MKT_ORDER:
        n = int(q[MKT_IDX[key]])
        if n <= 0:
            continue
        if key in ("HIRE", "BUY_LAND"):
            orders += [[key]] * n
        elif key.startswith("BUY_ANIMAL"):
            orders += [["BUY_ANIMAL", key.split(":")[1], 1]] * n
        else:
            op, it = key.split(":"); orders.append([op, it, n])
    return orders[:10]


def decode_unit(cls, unit_inv, shed):
    k = UNIT_OPS[int(cls)]
    if ":" not in k:
        return [k]
    op, it = k.split(":")
    if op == "PLANT":
        return ["PLANT", it]
    if op == "PICKUP":
        return ["PICKUP", it, max(1, int(shed.get(it, 1)))]
    return ["PLACE", it, max(1, int((unit_inv or {}).get(it, 1)))]
