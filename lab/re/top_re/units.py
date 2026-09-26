"""Legal, observation-driven unit dispatch for the standalone top-RE agent.

``act(obs, plan)`` returns ``(farmer_command, hand_commands)``.  The caller adds
the market action, so this module never emits one.  It intentionally relies only
on the current observation: a hand may disappear overnight and a worker's index
must therefore never be cached.

Plan contract (all fields optional; mapping or attributes are accepted):

* ``tasks(obs)`` -> task dictionaries, or ``tasks`` -> iterable.  A task has
  ``op``, ``target=(x,y)``, optional ``item``, ``quantity``, ``priority``.
* ``plant_targets``, ``build_targets``, ``place_targets``: ``{(x,y): item}``.
  ``build_targets`` values are ``PASTURE``/``COOP`` (or full BUILD_* operation).
* ``fertilize_targets`` / ``dig_targets``: iterable of coordinates.  Set
  ``fertilize_all=True`` to service all unfertilized plants.
* ``priority``: optional mapping overriding operation priorities;
  ``load_size`` (default 4) controls one shed pickup.

Unknown plan data is ignored.  This is deliberate: a bad target must become PASS,
not an engine silent no-op.  The legality rules match kaggle-environments 1.32.7
for the operations emitted here.  Movement is Manhattan because movement over a
LOCKED tile is legal; only tile operations require an owned tile.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional


MOVES = {
    "NORTH": (0, -1),
    "SOUTH": (0, 1),
    "EAST": (1, 0),
    "WEST": (-1, 0),
}
ANIMALS = {"COW": "PASTURE", "SHEEP": "PASTURE", "GOOSE": "COOP"}
FIRST_YIELD_DAY = {
    "WHEAT": 2,
    "CARROT": 2,
    "TOMATO": 8,
    "STRAWBERRY": 10,
    "MELON": 10,
}
PRODUCT_FOR_ANIMAL = {"COW": "MILK", "SHEEP": "WOOL", "GOOSE": "EGG"}
_CARGO_TO_KEEP = {"WHEAT", "FERTILIZER", *ANIMALS}
DEFAULT_PRIORITY = {
    "FEED": 260,
    "CARE": 230,
    "PLANT": 220,
    "BUILD_PASTURE": 215,
    "BUILD_COOP": 215,
    "PLACE": 210,
    "FERTILIZE": 185,
    "WATER": 170,
    "HARVEST": 160,
    "COLLECT_FERTILIZER": 150,
    "DIG": 145,
    "FETCH": 240,
    "DROP": 80,
}

# These are the MMPQ conditional-logit coefficients fitted by
# ``lab/re/task_logit.py``.  A bundled Kaggle agent has no adjacent JSON file,
# so this literal is the authoritative fallback; locally we also accept the
# fitted task_weights.json to make a refit immediately usable.
_WEIGHT_NAMES = (
    "WATER", "HARVEST_P", "HARVEST_A", "FEED", "CARE",
    "COLLECT_FERTILIZER", "PLANT", "DIG", "BUILD", "PLACE",
    "FERTILIZE", "dist", "log1p_dist", "unwatered", "unfed", "yield",
    "hour", "feed_needs_fetch", "water_x_hour",
)
_WEIGHT_VALUES = (
    0.29830579931433887, 0.0671040946792054, -0.17265410499451764,
    0.10546262000740361, 0.11983580041589408, 0.3800343153566766,
    0.2514896113763875, 0.013690389748303099, -0.1460021406695152,
    -0.031605376482775754, -0.8856610087513993, -1.1461936814955174,
    -0.43259014730261003, 0.19916721739468857, 0.04805598104353318,
    0.07498254425595476, 1.7664124801432992e-18, 0.10546262000740361,
    0.1345397106986807,
)


def _load_weights() -> dict[str, float]:
    """Load a local refit when available, with bundle-safe fixed fallback."""
    fallback = dict(zip(_WEIGHT_NAMES, _WEIGHT_VALUES))
    try:
        path = Path(__file__).with_name("task_weights.json")
        data = json.loads(path.read_text())
        names, values = data.get("names"), data.get("w")
        if isinstance(names, list) and isinstance(values, list) and len(names) == len(values):
            parsed = {str(name): float(value) for name, value in zip(names, values)}
            if set(_WEIGHT_NAMES) <= set(parsed):
                return parsed
    except (OSError, TypeError, ValueError, json.JSONDecodeError, NameError):
        # ``__file__`` is absent inside the one-file bundle.  The fallback is
        # intentional and gives the bundle precisely the checked-in fit.
        pass
    return fallback


TASK_WEIGHTS = _load_weights()
# The learned distance coefficient becomes an explicit movement cost.  Scaling
# both terms leaves the fitted trade-offs unchanged while avoiding tiny floats.
_UTILITY_SCALE = 10.0
_MOVE_COST = abs(TASK_WEIGHTS["dist"]) * _UTILITY_SCALE
_DUMMY_COST = 200.0


@dataclass(frozen=True)
class Task:
    op: str
    target: tuple[int, int]
    item: Optional[str] = None
    quantity: int = 1
    priority: int = 0
    source: str = "generated"

    @property
    def key(self) -> tuple[Any, ...]:
        return (self.op, self.target, self.item, self.quantity, self.source)


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _call_or_value(plan: Any, name: str, obs: Mapping[str, Any], default: Any) -> Any:
    value = _value(plan, name, default)
    if callable(value):
        try:
            return value(obs)
        except TypeError:
            return value()
    return value


def _xy(value: Any) -> Optional[tuple[int, int]]:
    if isinstance(value, str):
        try:
            x, y = value.split(",")
            return (int(x), int(y))
        except (TypeError, ValueError):
            return None
    if isinstance(value, (tuple, list)) and len(value) == 2:
        try:
            return (int(value[0]), int(value[1]))
        except (TypeError, ValueError):
            return None
    return None


def _targets(value: Any) -> Iterable[tuple[tuple[int, int], Any]]:
    if isinstance(value, Mapping):
        for target, item in value.items():
            xy = _xy(target)
            if xy is not None:
                yield xy, item
    elif isinstance(value, (list, tuple, set)):
        for target in value:
            xy = _xy(target)
            if xy is not None:
                yield xy, None


def _task_from_raw(raw: Any) -> Optional[Task]:
    if isinstance(raw, Task):
        return raw
    if not isinstance(raw, Mapping):
        return None
    op = str(raw.get("op", "")).upper()
    target = _xy(raw.get("target"))
    if not op or target is None:
        return None
    try:
        quantity = max(1, int(raw.get("quantity", 1)))
        priority = int(raw.get("priority", DEFAULT_PRIORITY.get(op, 0)))
    except (TypeError, ValueError):
        return None
    item = raw.get("item")
    return Task(op, target, str(item).upper() if item is not None else None,
                quantity, priority, str(raw.get("source", "plan")))


class _World:
    def __init__(self, obs: Mapping[str, Any]):
        self.obs = obs
        self.player = int(obs.get("player", 0))
        farms = obs.get("farms", [])
        if not isinstance(farms, list) or not (0 <= self.player < len(farms)):
            raise ValueError("observation has no own farm")
        self.farm = farms[self.player]
        self.private = obs.get("private", {}) or {}
        self.tiles = self.farm.get("tiles", []) or []
        self.height = len(self.tiles)
        self.width = len(self.tiles[0]) if self.height else 0
        self.day = int(obs.get("step", int(obs.get("day", 0)) * 24) or 0) // 24
        self.positions = [self.farm.get("farmer", [0, 0]), *(self.farm.get("hands", []) or [])]
        inventories = self.private.get("inventories", []) or []
        self.inventories = [dict(inventories[i]) if i < len(inventories) else {}
                            for i in range(len(self.positions))]
        self.seeds = self.private.get("seeds", {}) or {}
        self.shed = self.private.get("shed", {}) or {}
        self.shed_capacity = int(obs.get("configuration", {}).get(
            "shedCapacity", self.private.get("shed_capacity", 100)) or 100)
        self.reserved_seed: dict[str, int] = {}
        self.reserved_pickup: dict[str, int] = {}

    def in_bounds(self, xy: tuple[int, int]) -> bool:
        x, y = xy
        return 0 <= x < self.width and 0 <= y < self.height

    def tile(self, xy: tuple[int, int]) -> Any:
        x, y = xy
        return self.tiles[y][x] if self.in_bounds(xy) else "LOCKED"

    def owned(self, xy: tuple[int, int]) -> bool:
        return self.in_bounds(xy) and self.tile(xy) != "LOCKED"

    def shed_tiles(self) -> tuple[tuple[int, int], ...]:
        # The official board is 10x10; retain the same central four for tests.
        half_x, half_y = self.width // 2, self.height // 2
        return ((half_x - 1, half_y - 1), (half_x, half_y - 1),
                (half_x - 1, half_y), (half_x, half_y))

    def at_shed(self, xy: tuple[int, int]) -> bool:
        return xy in self.shed_tiles()

    def room(self) -> int:
        return max(0, self.shed_capacity - sum(max(0, int(v)) for v in self.shed.values()))


def _position(world: _World, actor: int) -> tuple[int, int]:
    pos = world.positions[actor]
    return (int(pos[0]), int(pos[1]))


def _distance(left: tuple[int, int], right: tuple[int, int]) -> int:
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _step_toward(start: tuple[int, int], target: tuple[int, int]) -> list[str]:
    x, y = start
    tx, ty = target
    if x < tx:
        return ["EAST"]
    if x > tx:
        return ["WEST"]
    if y < ty:
        return ["SOUTH"]
    if y > ty:
        return ["NORTH"]
    return ["PASS"]


def _mature_harvestable(world: _World, tile: Mapping[str, Any]) -> bool:
    if int(tile.get("yield_units", 0) or 0) <= 0:
        return False
    if "animal" in tile:
        return True
    crop = str(tile.get("crop", "")).upper()
    planted = int(tile.get("planted_day", world.day) or world.day)
    return crop in FIRST_YIELD_DAY and world.day - planted >= FIRST_YIELD_DAY[crop]


def _operation_legal(world: _World, actor: int, task: Task) -> bool:
    """True only if task's non-movement command would execute now at target."""
    xy, op, item = task.target, task.op, task.item
    if not world.in_bounds(xy):
        return False
    inv = world.inventories[actor]
    tile = world.tile(xy)
    if op == "FETCH":
        return (world.at_shed(xy) and bool(item) and
                int(world.shed.get(item, 0) or 0) > world.reserved_pickup.get(item, 0))
    if op == "DROP":
        return world.at_shed(xy) and any(int(v) > 0 for item, v in inv.items()
                                          if item not in _CARGO_TO_KEEP) and \
            sum(max(0, int(v)) for v in inv.values()) <= world.room()
    if op == "PLACE":
        return (item in ANIMALS and isinstance(tile, Mapping) and
                tile.get("kind") == ANIMALS[item] and "animal" not in tile and
                int(inv.get(item, 0) or 0) > 0)
    if not world.owned(xy):
        return False
    if op == "PLANT":
        return (item in FIRST_YIELD_DAY and tile is None and
                int(world.seeds.get(item, 0) or 0) > world.reserved_seed.get(item, 0))
    if op == "WATER":
        return isinstance(tile, Mapping) and tile.get("kind") == "PLANT" and not tile.get("watered_today")
    if op == "HARVEST":
        return isinstance(tile, Mapping) and _mature_harvestable(world, tile)
    if op == "FERTILIZE":
        return (isinstance(tile, Mapping) and tile.get("kind") == "PLANT" and
                int(inv.get("FERTILIZER", 0) or 0) > 0)
    if op == "DIG":
        return tile is not None and not (isinstance(tile, Mapping) and "animal" in tile)
    if op in {"BUILD_PASTURE", "BUILD_COOP"}:
        return tile is None
    if op == "FEED":
        return (isinstance(tile, Mapping) and "animal" in tile and not tile.get("fed_today") and
                int(inv.get("WHEAT", 0) or 0) > 0)
    if op == "CARE":
        return isinstance(tile, Mapping) and "animal" in tile and not tile.get("cared_today")
    if op == "COLLECT_FERTILIZER":
        return isinstance(tile, Mapping) and "animal" in tile and bool(tile.get("fertilizer_available"))
    return False


def _command(world: _World, actor: int, task: Task) -> list[Any]:
    pos = _position(world, actor)
    if pos != task.target:
        return _step_toward(pos, task.target)
    if not _operation_legal(world, actor, task):
        return ["PASS"]
    if task.op == "FETCH":
        available = int(world.shed.get(task.item, 0) or 0) - world.reserved_pickup.get(task.item, 0)
        return ["PICKUP", task.item, min(task.quantity, available)]
    if task.op == "DROP":
        return ["DROP"]
    if task.op == "PLACE":
        return ["PLACE", task.item]
    if task.op == "PLANT":
        return ["PLANT", task.item]
    return [task.op]


def _priority(plan: Any, op: str, fallback: int) -> int:
    table = _value(plan, "priority", {}) or {}
    try:
        return int(table.get(op, fallback)) if isinstance(table, Mapping) else fallback
    except (TypeError, ValueError):
        return fallback


def _manual_tasks(plan: Any, obs: Mapping[str, Any]) -> list[Task]:
    raw = _call_or_value(plan, "tasks", obs, []) or []
    if isinstance(raw, Mapping):
        raw = raw.values()
    return [task for entry in raw if (task := _task_from_raw(entry)) is not None]


def _generated_tasks(world: _World, plan: Any) -> list[Task]:
    result: list[Task] = []
    add = result.append
    priority = lambda op: _priority(plan, op, DEFAULT_PRIORITY[op])

    for xy, crop in _targets(_call_or_value(plan, "plant_targets", world.obs, {})):
        crop = str(crop).upper() if crop is not None else ""
        tile = world.tile(xy)
        if isinstance(tile, Mapping) and tile.get("kind") == "WEED":
            add(Task("DIG", xy, priority=priority("DIG"), source="plant-clear"))
        else:
            add(Task("PLANT", xy, crop, priority=priority("PLANT"), source="plant"))

    for xy, structure in _targets(_call_or_value(plan, "build_targets", world.obs, {})):
        op = str(structure).upper() if structure is not None else ""
        if op in {"PASTURE", "COOP"}:
            op = "BUILD_" + op
        if op in {"BUILD_PASTURE", "BUILD_COOP"}:
            add(Task(op, xy, priority=priority(op), source="build"))

    for xy, animal in _targets(_call_or_value(plan, "place_targets", world.obs, {})):
        animal = str(animal).upper() if animal is not None else ""
        add(Task("PLACE", xy, animal, priority=priority("PLACE"), source="place"))

    dig = set(_xy(xy) for xy, _ in _targets(_call_or_value(plan, "dig_targets", world.obs, ())) )
    fert = set(_xy(xy) for xy, _ in _targets(_call_or_value(plan, "fertilize_targets", world.obs, ())) )
    if bool(_value(plan, "fertilize_all", False)):
        fert.update((x, y) for y, row in enumerate(world.tiles) for x, tile in enumerate(row)
                    if isinstance(tile, Mapping) and tile.get("kind") == "PLANT")

    for y, row in enumerate(world.tiles):
        for x, tile in enumerate(row):
            xy = (x, y)
            if xy in dig:
                add(Task("DIG", xy, priority=priority("DIG"), source="dig"))
            if not isinstance(tile, Mapping):
                continue
            if _mature_harvestable(world, tile):
                add(Task("HARVEST", xy, priority=priority("HARVEST"), source="harvest"))
            if tile.get("kind") == "PLANT":
                if not tile.get("watered_today"):
                    add(Task("WATER", xy, priority=priority("WATER"), source="water"))
                if xy in fert and int(tile.get("fertilized_until_day", -1) or -1) < world.day + 2:
                    add(Task("FERTILIZE", xy, priority=priority("FERTILIZE"), source="fertilize"))
            elif "animal" in tile:
                if not tile.get("fed_today"):
                    add(Task("FEED", xy, priority=priority("FEED"), source="feed"))
                if not tile.get("cared_today"):
                    add(Task("CARE", xy, priority=priority("CARE"), source="care"))
                if tile.get("fertilizer_available"):
                    add(Task("COLLECT_FERTILIZER", xy, priority=priority("COLLECT_FERTILIZER"), source="collect"))
    return result


def _needs_item(tasks: Iterable[Task], item: str) -> int:
    if item == "WHEAT":
        return sum(task.op == "FEED" for task in tasks)
    if item == "FERTILIZER":
        return sum(task.op == "FERTILIZE" for task in tasks)
    return sum(task.op == "PLACE" and task.item == item for task in tasks)


def _logistics_tasks(world: _World, plan: Any, tasks: list[Task]) -> list[Task]:
    result: list[Task] = []
    load = max(1, int(_value(plan, "load_size", 4) or 4))
    pickup_target = min(world.shed_tiles(), key=lambda xy: (xy[1], xy[0]))
    carried = {item: sum(int(inv.get(item, 0) or 0) for inv in world.inventories)
               for item in ("WHEAT", "FERTILIZER", *ANIMALS)}
    for item in ("WHEAT", "FERTILIZER", *ANIMALS):
        missing = max(0, _needs_item(tasks, item) - carried.get(item, 0))
        stock = int(world.shed.get(item, 0) or 0)
        if missing and stock:
            # Several runners may be sent to the shed in the same turn.  For
            # WHEAT each load corresponds to the unfed animals on that
            # runner's prospective route, rather than a single-token pickup.
            remaining = min(missing, stock)
            batch = 1 if item in ANIMALS else load
            n = 0
            while remaining:
                amount = min(batch, remaining)
                result.append(Task("FETCH", pickup_target, item, amount,
                                   _priority(plan, "FETCH", DEFAULT_PRIORITY["FETCH"]),
                                   f"fetch-{item}-{n}"))
                remaining -= amount
                n += 1
    # Cargo delivery is deliberately lower-priority than same-day service.
    for actor, inv in enumerate(world.inventories):
        # WHEAT is route cargo: dropping it merely to collect it again makes
        # workers ping-pong at the shed and starves animals.  Likewise retain
        # fertilizer and animals until their target operation consumes them.
        if (any(int(v) > 0 for item, v in inv.items() if item not in _CARGO_TO_KEEP)
                and sum(int(v) for v in inv.values()) <= world.room()):
            target = min(world.shed_tiles(), key=lambda xy: _distance(_position(world, actor), xy))
            result.append(Task("DROP", target, priority=_priority(plan, "DROP", DEFAULT_PRIORITY["DROP"]),
                               source=f"drop-{actor}"))
    return result


def tasks(obs: Mapping[str, Any], plan: Any) -> list[Task]:
    """Expose generated tasks for diagnostics/tests; ``act`` also filters legality."""
    world = _World(obs)
    return _manual_tasks(plan, obs) + _generated_tasks(world, plan)


def _logit_op(task: Task, tile: Any) -> str:
    if task.op == "HARVEST":
        return "HARVEST_A" if isinstance(tile, Mapping) and tile.get("animal") else "HARVEST_P"
    if task.op in {"BUILD_COOP", "BUILD_PASTURE"}:
        return "BUILD"
    return task.op


def _task_utility(world: _World, actor: int, task: Task) -> float:
    """Conditional-logit utility for a legal endpoint, excluding distance.

    Distance belongs to the matching cost directly.  FETCH/DROP do not occur in
    the replay fit, so FETCH borrows the fitted FEED/fetch signal and DROP is a
    small delivery preference; both stay subordinate to real productive work.
    """
    tile = world.tile(task.target)
    op = _logit_op(task, tile)
    hour = int(world.obs.get("hour", int(world.obs.get("step", 0)) % 24) or 0) / 23.0
    inv = world.inventories[actor]
    features: dict[str, float] = {name: 0.0 for name in _WEIGHT_NAMES}
    if op in features:
        features[op] = 1.0
    if isinstance(tile, Mapping):
        if task.op == "WATER":
            features["unwatered"] = float(tile.get("consecutive_unwatered", 0) or 0)
        if task.op == "FEED":
            features["unfed"] = float(tile.get("consecutive_unfed", 0) or 0)
        if task.op == "HARVEST":
            features["yield"] = float(tile.get("yield_units", 0) or 0)
    features["hour"] = hour
    features["water_x_hour"] = hour if task.op == "WATER" else 0.0
    if task.op == "FETCH" and task.item == "WHEAT":
        features["FEED"] = 1.0
        features["feed_needs_fetch"] = 1.0
    if task.op == "DROP":
        features["HARVEST_P"] = 0.10
    utility = sum(TASK_WEIGHTS[name] * value for name, value in features.items()
                  if name not in {"dist", "log1p_dist"})
    # Conditional-logit recovers relative preferences from successful trips;
    # it cannot encode the hard engine constraint that a second missed feed
    # loses the animal.  Preserve that constraint as a small survival floor.
    # The paired FETCH bonus makes the floor actionable before a worker owns
    # wheat, rather than merely preferring a feed task it cannot execute.
    if task.op == "FEED":
        missed = float(tile.get("consecutive_unfed", 0) or 0) if isinstance(tile, Mapping) else 0.0
        utility += 1.20 + 1.50 * missed
    elif task.op == "FETCH" and task.item == "WHEAT":
        utility += 1.20
    # A plan-provided priority is only a deterministic tie-breaker, never a
    # substitute for the replay-estimated valuation.
    return _UTILITY_SCALE * utility + task.priority * 1e-4


def _hungarian(cost: list[list[float]]) -> list[int]:
    """Minimum-cost assignment for rows <= columns, using stdlib only.

    Returns one distinct column for every row.  The implementation is the
    classic O(n^2*m) potentials algorithm and deliberately supports padded
    dummy columns, so an idle worker is a valid outcome.
    """
    if not cost:
        return []
    n, m = len(cost), len(cost[0])
    if not n <= m or any(len(row) != m for row in cost):
        raise ValueError("Hungarian matrix must be rectangular with rows <= columns")
    u, v = [0.0] * (n + 1), [0.0] * (m + 1)
    p, way = [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = [math.inf] * (m + 1), [False] * (m + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], math.inf, 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1, p[j0] = way[j0], p[way[j0]]
            j0 = j1
            if j0 == 0:
                break
    assignment = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            assignment[p[j] - 1] = j - 1
    return assignment


def _reachable(world: _World, actor: int, task: Task) -> bool:
    """A move is allowed only toward an endpoint executable with current cargo."""
    return world.in_bounds(task.target) and _operation_legal(world, actor, task)


def act(obs: Mapping[str, Any], plan: Any) -> tuple[list[Any], list[list[Any]]]:
    """Assign legal work globally, then return one action for every unit.

    The assignment minimizes Manhattan movement cost minus the fitted task
    utility.  A unit therefore moves only toward a presently executable
    endpoint; FETCH tasks make cargo prerequisites explicit and avoid promising
    an illegal FEED/PLACE operation to an empty-handed worker.
    """
    try:
        world = _World(obs)
    except (KeyError, TypeError, ValueError, IndexError):
        return ["PASS"], []
    if not world.positions or not world.width or not world.height:
        return ["PASS"], [["PASS"] for _ in world.positions[1:]]

    candidates = tasks(obs, plan)
    candidates.extend(_logistics_tasks(world, plan, candidates))
    # Equivalent logical requests should not compete for columns.  Separate
    # FETCH batches intentionally remain distinct, as several hands can load
    # wheat at different shed-access tiles in the same turn.
    deduped: list[Task] = []
    seen: set[tuple[Any, ...]] = set()
    for task in candidates:
        key = task.key if task.op == "FETCH" else (task.op, task.target, task.item)
        if key not in seen:
            seen.add(key)
            deduped.append(task)
    candidates = deduped
    commands: list[list[Any]] = [["PASS"] for _ in world.positions]
    if not candidates:
        return commands[0], commands[1:]
    # Pad with one dummy job per worker.  Its finite cost is a fallback for an
    # idle worker, but any reachable farm task inside the 10x10 board wins.
    matrix: list[list[float]] = []
    for actor in range(len(world.positions)):
        row: list[float] = []
        for task in candidates:
            if _reachable(world, actor, task):
                distance = _distance(_position(world, actor), task.target)
                row.append(distance * _MOVE_COST - _task_utility(world, actor, task))
            else:
                row.append(1e9)
        row.extend([_DUMMY_COST] * len(world.positions))
        matrix.append(row)
    assignment = _hungarian(matrix)
    claimed: set[tuple[Any, ...]] = set()
    for actor, column in enumerate(assignment):
        if not (0 <= column < len(candidates)):
            continue
        task = candidates[column]
        claim = task.key if task.op == "FETCH" else (task.op, task.target, task.item)
        # Reservations are rechecked in deterministic worker order.  This is
        # needed for a plan whose requested seed count exceeds current stock.
        if claim in claimed or not _operation_legal(world, actor, task):
            continue
        command = _command(world, actor, task)
        if command == ["PASS"]:
            continue
        commands[actor], claimed = command, claimed | {claim}
        if task.op == "PLANT" and task.item:
            world.reserved_seed[task.item] = world.reserved_seed.get(task.item, 0) + 1
        if task.op == "FETCH" and task.item:
            world.reserved_pickup[task.item] = world.reserved_pickup.get(task.item, 0) + task.quantity

    return commands[0], commands[1:]


def action(obs: Mapping[str, Any], plan: Any) -> dict[str, Any]:
    """Convenience adapter for the Kaggle action shape (without market orders)."""
    farmer, hands = act(obs, plan)
    return {"farmer": farmer, "hands": hands}
