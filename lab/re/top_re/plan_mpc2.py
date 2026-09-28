"""One-day value-MPC plan layer.

Samples plausible *tomorrow* macros from the conditional flow model and chooses
the one with the largest value-model final-margin estimate.  It deliberately
does not roll the world model past tomorrow: repeated learned transitions made
the previous MPC compound model error.  Exports the same desired/targets
interface as plan.py and plan_fm.py.
"""
import math
try:
    import numpy as _np
except Exception:
    _np = None

MPC2 = None  # filled by bundle (TOPRE_MODEL json)
CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]
ANIMALS = ["COW", "SHEEP", "GOOSE"]
SHOPS = ["BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE", "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET"]
ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))

# Small and fixed: one batch at the first call of a day, cached for its rest.
K, FLOW_STEPS, TRUST_MARGIN = 12, 8, 3000.0
_CACHE, _WEIGHTS, _AGENT = {}, None, None

def _lin(W, b, x):
    return x @ W.T + b

def _silu(x):
    return x / (1.0 + _np.exp(-_np.clip(x, -60.0, 60.0)))

def _weights():
    global _WEIGHTS
    if _WEIGHTS is None:
        _WEIGHTS = {
            name: [(_np.asarray(W, _np.float32), _np.asarray(b, _np.float32)) for W, b in MPC2[name]["W"]]
            for name in ("wm", "value")
        }
    return _WEIGHTS

def _net(name, x):
    for i, (W, b) in enumerate(_weights()[name]):
        x = _lin(W, b, x)
        if i + 1 < len(_weights()[name]): x = _silu(x)
    return x

def _normal(s):
    return "".join(c for c in s.lower() if c.isalnum())

def _distance(a, b):
    """Deterministic name distance for the documented non-top_re fallback."""
    a, b = _normal(a), _normal(b)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        row = [i]
        for j, cb in enumerate(b, 1):
            row.append(min(row[-1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = row
    return prev[-1]

def _agent_onehot():
    global _AGENT
    if _AGENT is None:
        names = list(MPC2.get("agents") or [])
        if not names:
            _AGENT = _np.zeros((0,), _np.float32)
        else:
            target = _normal("top_re")
            exact = [i for i, name in enumerate(names) if _normal(str(name)) == target]
            ix = exact[0] if exact else min(range(len(names)), key=lambda i: (_distance("top_re", str(names[i])), _normal(str(names[i]))))
            _AGENT = _np.zeros((len(names),), _np.float32); _AGENT[ix] = 1.0
    return _AGENT

def _macro(farm):
    crops, animals = {}, {}; structs = {"PASTURE": 0, "COOP": 0}; fert = empty = 0
    for row in farm["tiles"]:
        for tile in row:
            if tile is None:
                empty += 1
            elif isinstance(tile, dict):
                kind = tile.get("kind")
                if kind == "PLANT":
                    crop = tile.get("crop"); crops[crop] = crops.get(crop, 0) + 1
                    fert += int(tile.get("fertilized_until_day", -1) >= 0)
                elif kind in structs:
                    structs[kind] += 1
                    animal = tile.get("animal")
                    if animal: animals[animal] = animals.get(animal, 0) + 1
    return [crops.get(c, 0) for c in CROPS] + [animals.get(a, 0) for a in ANIMALS] + [
        structs["PASTURE"], structs["COOP"], len(farm.get("unlocked_quadrants") or ["NW"]),
        len(farm.get("hands") or []), math.log1p(max(0.0, float(farm["money"]))), fert, empty,
    ]

def _shops(obs):
    unlocked = (obs.get("town") or {}).get("unlocked_shops", [])
    return [float(sum(shop == name for shop in unlocked)) for name in SHOPS]

def _tomorrow(me, day, shops, opponent, seed):
    """K sampled one-day FM outcomes, ranked by expected final margin only."""
    if _np is None:
        return me  # Safe, deterministic degradation if the game image lacks numpy.
    wm, value = MPC2["wm"], MPC2["value"]
    mux, sdx = _np.asarray(wm["mu_x"], _np.float32), _np.maximum(_np.asarray(wm["sd_x"], _np.float32), 1e-3)
    mud, sdd = _np.asarray(wm["mu_d"], _np.float32), _np.maximum(_np.asarray(wm["sd_d"], _np.float32), 1e-3)
    current = _np.asarray(me, _np.float32)
    agent = _agent_onehot()
    cond = _np.concatenate(((current - mux) / sdx, [min(29, day) / 29.0], shops, opponent, agent)).astype(_np.float32)
    rng = _np.random.default_rng(seed)
    z = rng.standard_normal((K, len(mud)), dtype=_np.float32)
    c = _np.broadcast_to(cond, (K, len(cond)))
    for step in range(FLOW_STEPS):
        t = _np.full((K, 1), step / FLOW_STEPS, _np.float32)
        z += _net("wm", _np.concatenate((z, t, c), axis=1)) / FLOW_STEPS
    candidates = current + z * sdd + mud
    vcond = _np.concatenate(((candidates - mux) / sdx, _np.full((K, 1), min(29, day + 1) / 29.0, _np.float32),
                             _np.broadcast_to(_np.asarray(shops + opponent, _np.float32), (K, len(shops) + len(opponent))),
                             _np.broadcast_to(agent, (K, len(agent)))), axis=1)
    value_out = _net("value", vcond) * _np.asarray(value["sd"], _np.float32) + _np.asarray(value["mu"], _np.float32)
    # Penalise only an abnormal one-day displacement; output 0 is E[final margin].
    trust = _np.mean(((candidates - current - mud) / sdd) ** 2, axis=1)
    return candidates[int(_np.argmax(value_out[:, 0] - TRUST_MARGIN * trust))].tolist()

def _target(obs, player):
    key = (player, int(obs["day"]))
    if key not in _CACHE:
        me = _macro(obs["farms"][player]); opponent = _macro(obs["farms"][1 - player])
        _CACHE[key] = _tomorrow(me, int(obs["day"]), _shops(obs), opponent, 1009 * int(obs["day"]) + player)
    return _CACHE[key]

def _dist(tile):
    return min(abs(tile[0] - x) + abs(tile[1] - y) for x, y in ACCESS)

def desired(obs, player):
    target = _target(obs, player); day = int(obs["day"]); tiles = obs["farms"][player]["tiles"]
    crop_goal = {crop: max(0, int(round(target[i]))) for i, crop in enumerate(CROPS)}
    animal_goal = {animal: max(0, int(round(target[5 + i]))) for i, animal in enumerate(ANIMALS)}
    want, have_crop = {}, {crop: 0 for crop in CROPS}; have_animal = {animal: 0 for animal in ANIMALS}; free = []
    for y in range(10):
        for x in range(10):
            tile = tiles[y][x]
            if tile == "LOCKED": continue
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                crop = tile.get("crop"); want[(x, y)] = crop; have_crop[crop] = have_crop.get(crop, 0) + 1
            elif isinstance(tile, dict) and tile.get("kind") in ("PASTURE", "COOP"):
                kind = tile["kind"]; animal = tile.get("animal") or ("GOOSE" if kind == "COOP" else ("COW" if have_animal["COW"] < animal_goal["COW"] else "SHEEP"))
                want[(x, y)] = kind + ":" + animal; have_animal[animal] += 1
            else:
                free.append((x, y))
    free.sort(key=lambda tile: (_dist(tile), tile[1], tile[0]))
    for animal in ANIMALS:
        for _ in range(max(0, animal_goal[animal] - have_animal[animal])):
            if not free: break
            want[free.pop(0)] = ("COOP:" if animal == "GOOSE" else "PASTURE:") + animal
    if day < 28:
        for crop in sorted(CROPS, key=lambda c: -(crop_goal[c] - have_crop[c])):
            for _ in range(max(0, crop_goal[crop] - have_crop[crop])):
                if not free: break
                want[free.pop(0)] = crop
    return want

def targets(obs, player):
    target = _target(obs, player); step = int(obs.get("step", 0)); quads = len(obs["farms"][player].get("unlocked_quadrants") or ["NW"])
    land = {quads + 1: step} if target[10] > quads + 0.35 else {}
    return {"hands": max(3, min(12, int(round(target[11])))) if int(obs["day"]) < 29 else 8,
            "land_step": land, "wheat_reserve_per_animal": 2}
