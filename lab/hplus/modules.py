"""Horizon+ capability modules, appended to an es1_g9 agent file. All default OFF => identical to the base agent.
build(base_main_py, genes, out) writes a self-contained main.py whose LAST callable is the wrapped `agent`."""
import json

MODULE_SRC = r'''
# ======================= Horizon+ modules (lab/hplus/modules.py) =======================
_HP = __HP_GENES__
_HP_FIRST_YIELD = {"WHEAT": 2, "CARROT": 2, "TOMATO": 8, "STRAWBERRY": 10, "MELON": 10}
_HP_STATS = {"m1_fills": 0, "land_early": 0, "land_absorbed": 0}
_HP_LAND = {}   # player -> {"owed": int, "done": set(tape steps accelerated)}
_HP_LAND_COST = [1000, 2000, 4000]

def _hp_land(obs, action):
    """Macro L: buy a quadrant up to land_k steps before the current Horizon tape plans it (if cash stays >= buffer);
    then drop the next Horizon BUY_LAND (from tape or any layer) so the total number of quadrants is unchanged."""
    p = int(obs["player"]); step = int(obs["step"])
    st = _HP_LAND.setdefault(p, {"owed": 0, "done": set()})
    if step == 0:
        st["owed"] = 0; st["done"] = set()
    orders = [list(o) for o in (action.get("market") or [])]
    if st["owed"] > 0:
        kept = []
        for o in orders:
            if o and o[0] == "BUY_LAND" and st["owed"] > 0:
                st["owed"] -= 1; _HP_STATS["land_absorbed"] += 1
            else:
                kept.append(o)
        orders = kept
    try:
        cst = _IMPL.chassis.players.get(p) or {}
        tape = _IMPL.chassis.routes.get(cst.get("route"))
    except Exception:
        tape = None
    if tape and len(orders) < 10 and not any(o and o[0] == "BUY_LAND" for o in orders):
        for t in range(step + 1, min(len(tape), step + 1 + int(_HP["land_k"]))):
            a = tape[t] if isinstance(tape[t], dict) else {}
            if t not in st["done"] and any(o and o[0] == "BUY_LAND" for o in (a.get("market") or [])):
                farm = obs["farms"][p]; nq = len(farm.get("unlocked_quadrants") or []) - 1
                if nq < 3 and float(farm["money"]) - _HP_LAND_COST[nq] >= float(_HP["land_buffer"]):
                    orders.append(["BUY_LAND"]); st["owed"] += 1; st["done"].add(t); _HP_STATS["land_early"] += 1
                break
    return dict(action, market=orders)

def _hp_tile_op(tile, inv, day, allowed):
    """Best productive in-place op on this tile (M1), following engine semantics; None if nothing useful."""
    if not isinstance(tile, dict):
        return None
    inv = inv or {}
    if tile.get("kind") == "PLANT":
        age = day - int(tile.get("planted_day", day))
        if "HARVEST_PLANT" in allowed and age >= _HP_FIRST_YIELD.get(tile.get("crop"), 99) and int(tile.get("yield_units", 0)) > 0:
            return ["HARVEST"]
        if "FERTILIZE" in allowed and inv.get("FERTILIZER", 0) > 0 and tile.get("crop") in _HP["m1_fert_crops"] \
                and int(tile.get("fertilized_until_day", -1)) < day:
            return ["FERTILIZE"]
        if "WATER" in allowed and not tile.get("watered_today"):
            return ["WATER"]
        return None
    if "animal" in tile:
        if "HARVEST_ANIMAL" in allowed and int(tile.get("yield_units", 0)) > 0:
            return ["HARVEST"]
        if "COLLECT_FERTILIZER" in allowed and tile.get("fertilizer_available"):
            return ["COLLECT_FERTILIZER"]
        if "CARE" in allowed and not tile.get("cared_today"):
            return ["CARE"]
        if "FEED" in allowed and not tile.get("fed_today") and inv.get("WHEAT", 0) > 0:
            return ["FEED"]
    return None

_HP_BASE_AGENT = agent
del agent  # kaggle loader takes the LAST-inserted callable: re-insert `agent` at the end


def agent(obs, config=None):
    action = _HP_BASE_AGENT(obs, config)
    try:
        if _HP.get("land_on"):
            action = _hp_land(obs, action)
    except Exception:
        pass
    try:
        if not _HP.get("m1_on"):
            return action
        step = int(obs["step"]); day = step // 24
        if not (_HP["m1_day0"] <= day <= _HP["m1_day1"]) or step >= 718:
            return action
        p = int(obs["player"]); farm = obs["farms"][p]; priv = obs.get("private") or {}
        invs = priv.get("inventories") or []
        pos = [farm["farmer"]] + list(farm.get("hands") or [])
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        allowed = set(_HP["m1_ops"])
        for i, u in enumerate(units):
            if i >= len(pos) or (u and u[0] != "PASS"):
                continue
            x, y = pos[i]
            op = _hp_tile_op(farm["tiles"][y][x], invs[i] if i < len(invs) else {}, day, allowed)
            if op:
                units[i] = op; _HP_STATS["m1_fills"] += 1
        action = dict(action, farmer=units[0], hands=units[1:])
    except Exception:
        pass
    return action
'''

DEFAULT = {"m1_on": False, "m1_day0": 0, "m1_day1": 29, "m1_ops": ["HARVEST_ANIMAL", "COLLECT_FERTILIZER", "CARE", "WATER", "FERTILIZE"],
           "m1_fert_crops": ["STRAWBERRY", "TOMATO"],
           "land_on": False, "land_k": 24, "land_buffer": 300}

def build(base, genes, out):
    g = dict(DEFAULT); g.update(genes or {})
    src = open(base).read().rstrip() + "\n" + MODULE_SRC.replace("__HP_GENES__", repr(g))
    open(out, "w").write(src)
    return g
