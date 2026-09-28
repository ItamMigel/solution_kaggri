"""Clone-safe, default-off reactive third-land / tomato-goose lane.

The decision deliberately happens *after* the shared Horizon clone detector's
first useful window.  Until six positional observations (216..222) have
arrived this wrapper only forwards the frozen es7_wm action.  A single equal
position makes the episode permanently ineligible, so tape clones retain the
exact parent action stream.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT: dict[str, Any] = {"reactive_lane": False}


MODULE_SRC = r'''
# ================= clone-safe reactive lane (lab/hplus/reactive_lane.py) =================
_RLN = __RLN_GENES__
_RLN_STATE = {}
_RLN_REPORT = {"checks": 0, "matches": 0, "nonclone": 0, "clone": 0,
               "early_checks": 0, "early_matches": 0, "early_nonclone": 0,
               "early_clone": 0, "reserve_wheat_skips": 0,
               "land_orders": 0, "land_confirmed": 0, "launches": 0,
               "tomato_plants": 0, "goose_places": 0, "service": 0,
               "aborts": 0, "errors": 0}
_RLN_PARENT = agent
del agent

def _rln_abort(st, reason="unknown"):
    if not st.get("aborted"):
        st["aborted"] = True; st["abort_reason"] = reason; _RLN_REPORT["aborts"] += 1

def _rln_walk(pos, target):
    x, y = int(pos[0]), int(pos[1]); tx, ty = target
    if x != tx: return ["EAST" if x < tx else "WEST"]
    if y != ty: return ["SOUTH" if y < ty else "NORTH"]
    return None

def _rln_clone_check(obs, st):
    """Use the inherited `_race_positions_equal` predicate, once per step only."""
    step = int(obs["step"])
    if st.get("decision") is not None or not 216 <= step <= 222 or st.get("checked_step") == step:
        return
    st["checked_step"] = step; st["checks"] += 1; _RLN_REPORT["checks"] += 1
    equal = bool(_race_positions_equal(obs["farms"], int(obs["player"])))
    st["matches"] += int(equal); _RLN_REPORT["matches"] += int(equal)
    # The bounded 216..222 window has seven callbacks.  Do not decide before
    # six actual checks, even after an early match: the public contract is
    # explicitly a six-check test, not an opportunistic one-check shortcut.
    if st["checks"] >= 6:
        st["decision"] = st["matches"] == 0
        _RLN_REPORT["nonclone" if st["decision"] else "clone"] += 1

def _rln_early_check(obs, st):
    """A clone-safe early signal used only to preserve cash before d9.

    Tape clones have the same farmer coordinate from the opening.  A single
    equality permanently disables the reserve.  Conversely, six distinct
    early observations with no equality only make the market reserve eligible;
    the stronger 216..222 gate still controls all land and unit actions.
    """
    step = int(obs["step"])
    if st.get("early_decision") is not None or not 0 <= step <= 167 or st.get("early_checked_step") == step:
        return
    st["early_checked_step"] = step
    own, rival = obs["farms"][int(obs["player"])], obs["farms"][1 - int(obs["player"])]
    equal = own.get("farmer") == rival.get("farmer")
    st["early_checks"] += 1; st["early_matches"] += int(equal)
    _RLN_REPORT["early_checks"] += 1; _RLN_REPORT["early_matches"] += int(equal)
    if equal:
        st["early_decision"] = False; _RLN_REPORT["early_clone"] += 1
    elif st["early_checks"] >= 6:
        st["early_decision"] = True; _RLN_REPORT["early_nonclone"] += 1

def _rln_reserve_cash(obs, action, st):
    """Keep d6--8 cash by dropping only a discretionary WHEAT product buy.

    This layer cannot create an order or alter any worker action.  It runs
    only after the early non-clone signal; clones have already returned the
    frozen parent action object unchanged.
    """
    step = int(obs["step"])
    if st.get("early_decision") is not True or not 144 <= step <= 215:
        return action
    market = action.get("market") or []
    filtered = [o for o in market if not (isinstance(o, list) and len(o) >= 2
                and o[0] == "BUY_PRODUCT" and o[1] == "WHEAT")]
    if len(filtered) == len(market):
        return action
    _RLN_REPORT["reserve_wheat_skips"] += len(market) - len(filtered)
    return dict(action, market=[list(o) if isinstance(o, list) else o for o in filtered])

def _rln_owned_land(obs, action, st):
    """Accelerate only the current route's existing d11 BUY_LAND, with debt cleanup."""
    p, step = int(obs["player"]), int(obs["step"])
    farm = obs["farms"][p]; quadrants = len(farm.get("unlocked_quadrants") or [])
    hp = _HP_LAND.get(p) or {}
    # A successful early order is observable before any launch; otherwise no
    # tomato/goose order is ever emitted.  Continue exactly long enough for
    # `_hp_land` to absorb its one inherited d11 order.
    if st.get("land_before") is not None and not st.get("land_confirmed"):
        if quadrants == st["land_before"] + 1:
            st["land_confirmed"] = True; _RLN_REPORT["land_confirmed"] += 1
        elif step > st.get("land_step", step) + 1:
            _rln_abort(st, "land_unconfirmed"); return action
    if st.get("aborted"):
        return action
    if st.get("land_confirmed") and not (hp.get("pending") is not None or int(hp.get("owed", 0)) > 0):
        return action
    if st.get("land_before") is None:
        # The parent owns an exact future land order.  Do not create a naked
        # BUY_LAND if its route has changed, the market lane is full, or this
        # is not the second-to-third quadrant transition.
        native = _IMPL.chassis.players.get(p) or {}; tape = _IMPL.chassis.routes.get(native.get("route")) or []
        future = range(step + 1, min(len(tape), step + 49))
        if quadrants != 2 or len(action.get("market") or []) >= 10 or not any(
                any(order and order[0] == "BUY_LAND" for order in (tape[t].get("market") or [])) for t in future):
            _rln_abort(st, "land_route_or_cash"); return action
        st["land_before"] = quadrants; st["land_step"] = step
    old_k, old_buffer = _HP["land_k"], _HP["land_buffer"]
    _HP["land_k"], _HP["land_buffer"] = 48, 300
    try:
        result = _hp_land(obs, action)
    finally:
        _HP["land_k"], _HP["land_buffer"] = old_k, old_buffer
    if result != action and st.get("land_order_step") is None:
        st["land_order_step"] = step; _RLN_REPORT["land_orders"] += 1
    return result

def _rln_start(obs, action, st):
    """Day-12 owned launch: two appended hands, one tomato and one goose.

    It is intentionally restricted to the route's quiet hour 289.  The
    parent must still emit its literal route market list there; this prevents
    a market-only launch if a preceding parent layer has changed the route.
    """
    p, step = int(obs["player"]), int(obs["step"])
    if st.get("launch") or step != 289:
        return action
    native = _IMPL.chassis.players.get(p) or {}; tape = _IMPL.chassis.routes.get(native.get("route")) or []
    parent_market = [list(o) for o in (action.get("market") or [])]
    expected = [list(o) for o in ((tape[step] if step < len(tape) else {}).get("market") or [])]
    farm, private = obs["farms"][p], obs.get("private") or {}
    if (parent_market != expected or len(parent_market) > 6 or float(farm.get("money", 0)) < 6000
            or private.get("seeds", {}).get("TOMATO", 0) or private.get("shed", {}).get("GOOSE", 0)):
        _rln_abort(st, "launch_precondition"); return action
    orders = parent_market + [["BUY_SEED", "TOMATO", 1], ["BUY_ANIMAL", "GOOSE", 1], ["HIRE"], ["HIRE"]]
    if len(orders) > 10:
        _rln_abort(st, "launch_slots"); return action
    st["launch"] = {"hands": len(farm.get("hands") or []), "step": step}; _RLN_REPORT["launches"] += 1
    return dict(action, market=orders)

def _rln_workers(obs, action, st):
    """Operate only the two observed appended hands; any ownership failure aborts."""
    p, step = int(obs["player"]), int(obs["step"]); launch = st.get("launch")
    if not launch or step < 290 or step >= 312 or st.get("aborted"):
        return action
    farm, private = obs["farms"][p], obs.get("private") or {}; hands = list(farm.get("hands") or [])
    if st.get("actors") is None:
        # Parent may have hired at 289 too, but our two orders are last, hence
        # their observed indices are the final two hands on the next callback.
        if len(hands) < int(launch["hands"]) + 2:
            _rln_abort(st, "workers_missing"); return action
        if int(private.get("seeds", {}).get("TOMATO", 0)) < 1 or int(private.get("shed", {}).get("GOOSE", 0)) < 1:
            _rln_abort(st, "purchases_missing"); return action
        st["actors"] = (len(hands) - 1, len(hands))  # command indices: farmer=0
    tomato, goose = st["actors"]
    positions = [farm["farmer"]] + hands; inventories = private.get("inventories") or []
    commands = [list(action.get("farmer") or ["PASS"])] + [list(c) for c in (action.get("hands") or [])]
    if len(commands) <= goose or len(positions) <= goose:
        _rln_abort(st, "command_shape"); return action
    # `_hp_land`'s owned d11 order opens SW (NW,NE -> NW,NE,SW), not
    # the later V219 SE investment.  Choose two *observed empty/weed* cells
    # in that exact newly owned quadrant; fixed cells can already hold parent
    # WHEAT by d12.  A later occupancy change is a hard abort.
    if st.get("sites") is None:
        free = [(x, y) for y in range(5, 10) for x in range(0, 5)
                if farm["tiles"][y][x] is None or (isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("kind") == "WEED")]
        if len(free) < 2: _rln_abort(st, "no_empty_third_land_sites"); return action
        st["sites"] = (free[0], free[1])
    tomato_site, goose_site = st["sites"]; shed_access = (4, 5)
    for site in (tomato_site, goose_site):
        if farm["tiles"][site[1]][site[0]] == "LOCKED": _rln_abort(st, "third_land_locked"); return action
    def inv(i): return inventories[i] if i < len(inventories) else {}
    # tomato worker: pickup -> walk -> one owned plant -> water/harvest/service
    pos, tile, cargo = positions[tomato], farm["tiles"][tomato_site[1]][tomato_site[0]], inv(tomato)
    # Seeds are planted directly from private seed stock (unlike animals,
    # which must be picked from the shed); V219 uses the same engine path.
    if tuple(pos) != tomato_site:
        commands[tomato] = _rln_walk(pos, tomato_site)
    elif isinstance(tile, dict) and tile.get("kind") == "WEED":
        commands[tomato] = ["DIG"]
    elif tile is None and int(private.get("seeds", {}).get("TOMATO", 0)) > 0:
        commands[tomato] = ["PLANT", "TOMATO"]
    elif isinstance(tile, dict) and tile.get("crop") == "TOMATO":
        if not tile.get("watered_today") and step < 696: commands[tomato] = ["WATER"]
        elif int(tile.get("yield_units", 0)) > 0: commands[tomato] = ["HARVEST"]
        else: commands[tomato] = ["PASS"]
    else:
        _rln_abort(st, "tomato_tile_drift"); return action
    # goose worker: pickup -> walk -> build/PLACE -> bounded in-place service.
    pos, tile, cargo = positions[goose], farm["tiles"][goose_site[1]][goose_site[0]], inv(goose)
    if int(cargo.get("GOOSE", 0)) <= 0 and not (isinstance(tile, dict) and tile.get("animal") == "GOOSE"):
        commands[goose] = _rln_walk(pos, shed_access) or ["PICKUP", "GOOSE", 1]
    elif tuple(pos) != goose_site:
        commands[goose] = _rln_walk(pos, goose_site)
    elif isinstance(tile, dict) and tile.get("kind") == "WEED":
        commands[goose] = ["DIG"]
    elif tile is None:
        commands[goose] = ["BUILD_COOP"]
    elif isinstance(tile, dict) and tile.get("kind") == "COOP" and "animal" not in tile and int(cargo.get("GOOSE", 0)):
        commands[goose] = ["PLACE", "GOOSE"]
    elif isinstance(tile, dict) and tile.get("animal") == "GOOSE":
        if int(tile.get("yield_units", 0)) > 0: commands[goose] = ["HARVEST"]
        elif not tile.get("fed_today") and int(cargo.get("WHEAT", 0)) > 0: commands[goose] = ["FEED"]
        elif not tile.get("cared_today"): commands[goose] = ["CARE"]
        else: commands[goose] = ["PASS"]
    else:
        _rln_abort(st, "goose_tile_drift"); return action
    if commands[tomato] == ["PLANT", "TOMATO"]: _RLN_REPORT["tomato_plants"] += 1
    if commands[goose] == ["PLACE", "GOOSE"]: _RLN_REPORT["goose_places"] += 1
    _RLN_REPORT["service"] += int(commands[tomato][0] in ("WATER", "HARVEST")) + int(commands[goose][0] in ("FEED", "CARE", "HARVEST"))
    return dict(action, farmer=commands[0], hands=commands[1:])

def agent(obs, config=None):
    action = _RLN_PARENT(obs, config)
    if not _RLN.get("reactive_lane"):
        return action
    try:
        p, step = int(obs["player"]), int(obs["step"])
        st = _RLN_STATE.get(p)
        if st is None or step <= st.get("last", -1):
            st = _RLN_STATE[p] = {"last": -1, "checks": 0, "matches": 0, "decision": None,
                                   "early_checks": 0, "early_matches": 0, "early_decision": None,
                                   "early_checked_step": -1,
                                   "checked_step": -1, "land_before": None, "land_confirmed": False,
                                   "land_order_step": None, "launch": None, "actors": None, "aborted": False}
        st["last"] = step; _rln_early_check(obs, st)
        action = _rln_reserve_cash(obs, action, st)
        _rln_clone_check(obs, st)
        if st.get("decision") is not True or st.get("aborted"):
            return action
        if 222 <= step <= 266 or (_HP_LAND.get(p) or {}).get("owed", 0):
            action = _rln_owned_land(obs, action, st)
        if st.get("land_confirmed") and not st.get("aborted"):
            action = _rln_start(obs, action, st)
            action = _rln_workers(obs, action, st)
        return action
    except Exception:
        _RLN_REPORT["errors"] += 1
        return action

agent.telemetry = _RLN_REPORT
'''


def normalise(genes: dict[str, Any] | None) -> dict[str, Any]:
    genes = {} if genes is None else genes
    if not isinstance(genes, dict) or set(genes) - set(DEFAULT):
        raise ValueError("only the reactive_lane boolean gene is supported")
    result = dict(DEFAULT); result.update(genes)
    if type(result["reactive_lane"]) is not bool:
        raise ValueError("reactive_lane must be bool")
    return result


def build(base_main_py: str | Path, genes: dict[str, Any] | None, out_main_py: str | Path) -> dict[str, Any]:
    g = normalise(genes); base, out = Path(base_main_py), Path(out_main_py)
    text = base.read_text().rstrip() + "\n" + MODULE_SRC.replace("__RLN_GENES__", repr(g))
    compile(text, str(out), "exec")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    info = {"base": str(base.resolve()), "genes": g, "default_off": not g["reactive_lane"],
            "clone_gate": "six checks in steps 216..222; any positional match is clone"}
    out.with_suffix(out.suffix + ".reactive_lane.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info
