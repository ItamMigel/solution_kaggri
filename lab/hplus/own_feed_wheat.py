"""T038 default-off own-feed WHEAT layer over a sealed Horizon build.

The layer has deliberately narrow authority.  It only replaces an inherited
``PASS`` on an already-empty owned tile with ``PLANT WHEAT``, using a seed that
is already present.  A plant is accepted only if the native continuation has
enough visits to harvest it.  When the visible herd has more three-day feed
demand than physical WHEAT plus this turn's actual product buys, it also removes
WHEAT sale orders, preserving their order slots as empty holes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT: dict[str, Any] = {
    "ofw_on": False,
    "ofw_day0": 10,
    "ofw_day1": 27,
    "ofw_horizon_days": 3,
    "ofw_max_plants": 2,
}


MODULE_SRC = r'''
# ================= T038 own-feed WHEAT (lab/hplus/own_feed_wheat.py) =================
_OFW = __OFW_GENES__
_OFW_PARENT = agent
del agent
_OFW_STATE = {}
_OFW_STATS = {"plants": 0, "sale_units_reserved": 0, "sale_turns_reserved": 0,
              "deficit_turns": 0, "path_abstains": 0, "shape_abstains": 0, "errors": 0}

def _ofw_stock(private):
    return max(0, int((private.get("shed") or {}).get("WHEAT", 0))) + sum(
        max(0, int(inv.get("WHEAT", 0))) for inv in (private.get("inventories") or []))

def _ofw_feed_need(farm, day, horizon):
    animals = []
    for row in farm.get("tiles") or []:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal") in ("COW", "SHEEP", "GOOSE"):
                animals.append(tile)
    # Today only animals not already fed need grain; every surviving animal needs
    # one unit on each following dawn.  This intentionally never predicts a new
    # animal purchase, so it cannot invent demand from an opponent/private state.
    return sum(0 if tile.get("fed_today") else 1 for tile in animals) + max(0, horizon - 1) * len(animals)

def _ofw_deficit(obs, action):
    seat = int(obs["player"]); farm = obs["farms"][seat]; private = obs.get("private") or {}
    incoming = sum(max(0, int(o[2])) for o in (action.get("market") or [])
                   if isinstance(o, list) and len(o) >= 3 and o[:2] == ["BUY_PRODUCT", "WHEAT"])
    return max(0, _ofw_feed_need(farm, int(obs["step"]) // 24, int(_OFW["ofw_horizon_days"])) - _ofw_stock(private) - incoming)

def _ofw_has_harvest_path(obs, action, pos, day):
    # CARROT2's exact tape-visit/yield model is already in the frozen parent.
    # It rejects a speculative PASS tile without a native watering+harvest path.
    visits = _ca_visits(obs, action, pos, min(719, (day + 6) * 24), start=int(obs["step"]) + 1)
    harvested, rescue, _ = _ca_yield_path("WHEAT", day, visits)
    return max(harvested, rescue) > 0

def agent(obs, config=None):
    action = _OFW_PARENT(obs, config)
    if not _OFW.get("ofw_on"):
        return action
    try:
        step = int(obs["step"]); day = step // 24
        if step >= 718 or not int(_OFW["ofw_day0"]) <= day <= int(_OFW["ofw_day1"]):
            return action
        deficit = _ofw_deficit(obs, action)
        if deficit <= 0:
            return action
        _OFW_STATS["deficit_turns"] += 1
        seat = int(obs["player"]); farm = obs["farms"][seat]; private = obs.get("private") or {}
        positions = [farm["farmer"], *(farm.get("hands") or [])]
        commands = [list(action.get("farmer") or ["PASS"]), *(list(c) for c in (action.get("hands") or []))]
        if len(positions) != len(commands):
            _OFW_STATS["shape_abstains"] += 1
            return action
        # Protect all parent same-turn wheat PLANTs: only truly spare existing seed
        # is available to this layer.  No buys, hires, movement, or route edits.
        seed = max(0, int((private.get("seeds") or {}).get("WHEAT", 0)) - sum(c[:2] == ["PLANT", "WHEAT"] for c in commands))
        planted = 0
        for i, (pos, command) in enumerate(zip(positions, commands)):
            if not seed or planted >= int(_OFW["ofw_max_plants"]) or command != ["PASS"]:
                continue
            x, y = int(pos[0]), int(pos[1])
            if farm["tiles"][y][x] is not None:
                continue
            if not _ofw_has_harvest_path(obs, action, (x, y), day):
                _OFW_STATS["path_abstains"] += 1
                continue
            commands[i] = ["PLANT", "WHEAT"]
            seed -= 1; planted += 1; _OFW_STATS["plants"] += 1
        market = [list(o) if isinstance(o, list) else o for o in (action.get("market") or [])]
        reserved = 0
        # A current three-day deficit means every physical WHEAT sale defeats the
        # feed reserve.  Empty lists preserve market-slot indices for the rival.
        for i, order in enumerate(market):
            if isinstance(order, list) and len(order) >= 3 and order[:2] == ["SELL", "WHEAT"]:
                reserved += max(0, int(order[2])); market[i] = []
        if reserved:
            _OFW_STATS["sale_units_reserved"] += reserved; _OFW_STATS["sale_turns_reserved"] += 1
        if not planted and not reserved:
            return action
        return dict(action, farmer=commands[0], hands=commands[1:], market=market)
    except Exception:
        _OFW_STATS["errors"] += 1
        return action

agent.telemetry = _OFW_STATS
'''


def normalise(genes: dict[str, Any] | None) -> dict[str, Any]:
    value = dict(DEFAULT)
    value.update(genes or {})
    if set(value) != set(DEFAULT):
        raise ValueError("unknown own-feed-wheat gene")
    if type(value["ofw_on"]) is not bool or any(type(value[key]) is not int for key in value if key != "ofw_on"):
        raise ValueError("invalid own-feed-wheat gene types")
    if not 0 <= value["ofw_day0"] <= value["ofw_day1"] <= 29 or not 1 <= value["ofw_horizon_days"] <= 4 or not 1 <= value["ofw_max_plants"] <= 4:
        raise ValueError("own-feed-wheat bounds invalid")
    return value


def build(base_main_py: str | Path, genes: dict[str, Any] | None, out_main_py: str | Path) -> dict[str, Any]:
    value = normalise(genes)
    base, out = Path(base_main_py), Path(out_main_py)
    src = base.read_text().rstrip() + "\n" + MODULE_SRC.replace("__OFW_GENES__", repr(value))
    compile(src, str(out), "exec")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(src)
    info = {"base": str(base.resolve()), "genes": value, "default_off": not value["ofw_on"]}
    out.with_suffix(out.suffix + ".own_feed_wheat.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info
