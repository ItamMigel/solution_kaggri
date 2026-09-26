#!/usr/bin/env python3
"""Build the T039 tape-aware crop-substitution experiment; never submits.

The final agent only substitutes a tape PLANT.  For the initial fixed rule it
keeps the first 24 strawberry tape plants and changes the later nine to wheat.
It simultaneously redirects only excess future strawberry seed orders, so a
replacement never consumes a strawberry seed.  A switched wheat tile remains
owned until the inherited strawberry watering tour revisits that very tile;
the last safe revisit (wheat age 3) becomes HARVEST.  This deliberately
does not claim that long-lived crop timing is interchangeable with short crop
timing: missed service is recorded and makes the enabled experiment fail its
audit rather than silently continuing.
"""
from __future__ import annotations

import argparse
from pathlib import Path


APPEND = r'''
# ================= T039 crop_mix: tape PLANT substitution =================
# Default-off.  Do not enable a target unless its crop timing has passed the
# official-engine audit: WHEAT/CARROT are finite, STRAWBERRY/TOMATO ongoing.
_CM = {"on": False, "targets": {"STRAWBERRY": 24},
       "replace": {"STRAWBERRY": "WHEAT"}}
_CM_CROP = {"WHEAT": {"first": 2, "last": 4, "ongoing": False},
            "CARROT": {"first": 2, "last": 3, "ongoing": False},
            "TOMATO": {"first": 8, "last": 8, "ongoing": True},
            "STRAWBERRY": {"first": 10, "last": 10, "ongoing": True},
            "MELON": {"first": 10, "last": 12, "ongoing": False}}
_CM_STATE = {}
_CM_STATS = {"swaps": 0, "seed_redirects": 0, "water_visits": 0,
             "service_ages": [], "harvests": 0, "missed_service": 0, "seed_blocks": 0,
             "tile_mismatches": 0, "errors": 0}


def _cm_tape(obs, step):
    seat = int(obs["player"])
    native = _IMPL.chassis.players.get(seat) or {}
    route = 2 if step >= 648 else native.get("route")
    tape = _IMPL.chassis.routes.get(route, ())
    return tape[step] if 0 <= step < len(tape) and isinstance(tape[step], dict) else {}


def _cm_tape_strawberry_rank(obs, step):
    """One-based rank of this tape strawberry PLANT, or zero if not one."""
    rank = 0
    for t in range(0, min(719, step) + 1):
        a = _cm_tape(obs, t)
        for c in [a.get("farmer")] + list(a.get("hands") or []):
            if c and c[:2] == ["PLANT", "STRAWBERRY"]:
                rank += 1
    return rank


def _cm_future_kept_strawberries(obs, after_step):
    """Number of original strawberry tape plants we still deliberately keep."""
    target = int(_CM["targets"].get("STRAWBERRY", 0))
    kept = 0
    for t in range(max(0, after_step), 719):
        a = _cm_tape(obs, t)
        for c in [a.get("farmer")] + list(a.get("hands") or []):
            if c and c[:2] == ["PLANT", "STRAWBERRY"] and _cm_tape_strawberry_rank(obs, t) <= target:
                kept += 1
    return kept


def _cm_live(farm, crop):
    return sum(1 for row in farm["tiles"] for tile in row
               if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") == crop)


_CM_PARENT = agent
del agent


def agent(obs, config=None):
    action = _CM_PARENT(obs, config)
    if not _CM.get("on"):
        return action
    try:
        step = int(obs["step"]); day = step // 24; seat = int(obs["player"])
        st = _CM_STATE.get(seat)
        if st is None or step <= st["step"]:
            st = _CM_STATE[seat] = {"step": -1, "tiles": {}}
            for key, value in list(_CM_STATS.items()):
                _CM_STATS[key] = [] if isinstance(value, list) else 0
        st["step"] = step
        if not isinstance(action, dict) or step >= 718:
            return action
        farm = obs["farms"][seat]; private = obs["private"]
        positions = [tuple(farm["farmer"])] + [tuple(p) for p in farm.get("hands") or []]
        units = [list(action.get("farmer") or ["PASS"])] + [list(c) for c in action.get("hands") or []]
        market = [list(o) for o in action.get("market") or []]
        changed = False

        # Resolve only our own finite replacement schedule.  The original
        # strawberry route revisits the same tile daily through age 3; that
        # last visit must harvest because the engine removes short crops at
        # the start of the nominal max-yield day.
        for xy, tile_st in list(st["tiles"].items()):
            tile = farm["tiles"][xy[1]][xy[0]]
            planted = tile_st["planted"]; crop = tile_st["crop"]
            if not (isinstance(tile, dict) and tile.get("kind") == "PLANT" and
                    tile.get("crop") == crop and int(tile.get("planted_day", -1)) == planted):
                st["tiles"].pop(xy, None); _CM_STATS["tile_mismatches"] += 1
                continue
            age = day - planted; spec = _CM_CROP[crop]
            if age > spec["last"]:
                st["tiles"].pop(xy, None); _CM_STATS["missed_service"] += 1
                continue
            here = next((i for i, pos in enumerate(positions) if pos == xy and i < len(units)), None)
            if here is None:
                continue
            cmd = units[here]
            # Retain the inherited water visit at age 2; use the next one for
            # harvest, before the finite crop's decay boundary.  We never
            # replace a movement or another productive operation.
            if cmd and cmd[0] == "WATER":
                _CM_STATS["water_visits"] += 1
                _CM_STATS["service_ages"].append(age)
                if age >= spec["last"] - 1 and int(tile.get("yield_units", 0)) > 0:
                    units[here] = ["HARVEST"]
                    st["tiles"].pop(xy, None); _CM_STATS["harvests"] += 1; changed = True

        # Redirect seed orders first.  Parent seed buys settle after unit
        # commands, so reserve exactly the kept future strawberry plants from
        # the observed pre-action stock; the excess order buys WHEAT instead.
        post_s = int(private.get("seeds", {}).get("STRAWBERRY", 0)) - sum(
            1 for c in units if c[:2] == ["PLANT", "STRAWBERRY"])
        reserve_s = _cm_future_kept_strawberries(obs, step + 1)
        rewritten = []
        for order in market:
            if len(order) >= 3 and order[:2] == ["BUY_SEED", "STRAWBERRY"]:
                quantity = max(0, int(order[2]))
                keep = min(quantity, max(0, reserve_s - post_s))
                post_s += keep
                if keep:
                    rewritten.append(["BUY_SEED", "STRAWBERRY", keep])
                redirect = quantity - keep
                if redirect:
                    rewritten.append(["BUY_SEED", "WHEAT", redirect])
                    _CM_STATS["seed_redirects"] += redirect; changed = True
            else:
                rewritten.append(order)
        market = rewritten

        # The fixed target uses the immutable tape rank, rather than a noisy
        # price rule.  It only fires after 24 live strawberries and only when
        # a physical wheat seed is already available this callback.
        target = int(_CM["targets"].get("STRAWBERRY", 24))
        wheat = int(private.get("seeds", {}).get("WHEAT", 0)) - sum(
            1 for c in units if c[:2] == ["PLANT", "WHEAT"])
        live_s = _cm_live(farm, "STRAWBERRY")
        for i, cmd in enumerate(units):
            if cmd[:2] != ["PLANT", "STRAWBERRY"] or i >= len(positions):
                continue
            rank = _cm_tape_strawberry_rank(obs, step)
            # More than one strawberry command can occur this step; rank is
            # only a target guard, while live count handles actual execution.
            if rank <= target or live_s < target:
                continue
            xy = positions[i]
            if wheat <= 0:
                _CM_STATS["seed_blocks"] += 1
                continue
            if farm["tiles"][xy[1]][xy[0]] is not None:
                continue
            units[i] = ["PLANT", "WHEAT"]; wheat -= 1; live_s += 0
            st["tiles"][xy] = {"planted": day, "crop": "WHEAT"}
            _CM_STATS["swaps"] += 1; changed = True
        if changed:
            return dict(action, farmer=units[0], hands=units[1:], market=market[:10])
    except Exception:
        _CM_STATS["errors"] += 1
    return action


agent.telemetry = _CM_STATS
'''


def build(base: Path, out: Path, *, enabled: bool) -> None:
    text = base.read_text() + "\n" + APPEND
    if enabled:
        text += "\n_CM['on'] = True\n"
    compile(text, str(out), "exec")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    p.add_argument("--enabled", action="store_true")
    a = p.parse_args(); build(a.base.resolve(), a.out.resolve(), enabled=a.enabled)


if __name__ == "__main__":
    main()
