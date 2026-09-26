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
        return world.at_shed(xy) and any(int(v) > 0 for v in inv.values()) and \
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
            amount = 1 if item in ANIMALS else min(load, missing, stock)
            result.append(Task("FETCH", pickup_target, item, amount,
                               _priority(plan, "FETCH", DEFAULT_PRIORITY["FETCH"]), "fetch"))
    # Cargo delivery is deliberately lower-priority than same-day service.
    for actor, inv in enumerate(world.inventories):
        if any(int(v) > 0 for v in inv.values()) and sum(int(v) for v in inv.values()) <= world.room():
            target = min(world.shed_tiles(), key=lambda xy: _distance(_position(world, actor), xy))
            result.append(Task("DROP", target, priority=_priority(plan, "DROP", DEFAULT_PRIORITY["DROP"]),
                               source=f"drop-{actor}"))
    return result


def tasks(obs: Mapping[str, Any], plan: Any) -> list[Task]:
    """Expose generated tasks for diagnostics/tests; ``act`` also filters legality."""
    world = _World(obs)
    return _manual_tasks(plan, obs) + _generated_tasks(world, plan)


def act(obs: Mapping[str, Any], plan: Any) -> tuple[list[Any], list[list[Any]]]:
    """Greedily reserve a legal current task and return one command per unit.

    A unit may travel toward a task whose endpoint is legal *now*.  Once it
    arrives, the endpoint is rechecked before emitting the operation; observation
    drift consequently turns into PASS rather than an invalid action.
    """
    try:
        world = _World(obs)
    except (KeyError, TypeError, ValueError, IndexError):
        return ["PASS"], []
    if not world.positions or not world.width or not world.height:
        return ["PASS"], [["PASS"] for _ in world.positions[1:]]

    candidates = tasks(obs, plan)
    candidates.extend(_logistics_tasks(world, plan, candidates))
    # One logical task / endpoint per tick.  CARE and FEED are intentionally
    # distinct: the engine permits them both on the same animal in one tick.
    claimed: set[tuple[str, tuple[int, int], Optional[str]]] = set()
    commands: list[list[Any]] = [["PASS"] for _ in world.positions]
    unused = set(range(len(world.positions)))

    ranked = sorted(enumerate(candidates), key=lambda pair: (
        -pair[1].priority, pair[1].target[1], pair[1].target[0], pair[1].op, pair[0]))
    for _, task in ranked:
        claim = (task.op, task.target, task.item)
        if claim in claimed:
            continue
        eligible = [actor for actor in unused if _operation_legal(world, actor, task)]
        if not eligible:
            continue
        actor = min(eligible, key=lambda i: (_distance(_position(world, i), task.target), i))
        command = _command(world, actor, task)
        if command == ["PASS"]:
            continue
        commands[actor] = command
        unused.remove(actor)
        claimed.add(claim)
        if task.op == "PLANT" and task.item:
            world.reserved_seed[task.item] = world.reserved_seed.get(task.item, 0) + 1
        if task.op == "FETCH" and task.item:
            world.reserved_pickup[task.item] = world.reserved_pickup.get(task.item, 0) + task.quantity
        if not unused:
            break

    return commands[0], commands[1:]


def action(obs: Mapping[str, Any], plan: Any) -> dict[str, Any]:
    """Convenience adapter for the Kaggle action shape (without market orders)."""
    farmer, hands = act(obs, plan)
    return {"farmer": farmer, "hands": hands}

