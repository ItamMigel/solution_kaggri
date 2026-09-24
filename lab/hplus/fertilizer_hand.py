"""A bounded, appended fertilizer-hand capability for Horizon+.

``build`` may be applied after :mod:`lab.hplus.modules.build`: it only appends a
last wrapper and therefore leaves Claude's M1/macros untouched.  The extra hand
is explicitly a daily rental, never an existing tape hand.  Default-off wrappers
are action-equivalent to their input agent.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any


DEFAULT: dict[str, Any] = {
    "fh_on": False,
    "fh_day0": 5,
    "fh_day1": 20,
    "fh_min_targets": 1,
    "fh_take": 2,
    "fh_cash_buffer": 1500,
    "fh_crops": ["STRAWBERRY", "TOMATO"],
}


MODULE_SRC = r'''
# ================= Horizon+ appended fertilizer hand (lab/hplus/fertilizer_hand.py) =================
_FH = __FH_GENES__
_FH_STATE = {}
_FH_STATS = {"hire_attempts": 0, "hires": 0, "spawn_mismatch": 0,
             "pickup": 0, "fertilize": 0, "moves": 0, "skips": 0}
_FH_ACCESS = ((4, 4), (5, 4), (4, 5), (5, 5))

def _fh_fib(n):
    a, b = 1, 1
    for _ in range(max(0, int(n))):
        a, b = b, a + b
    return a

def _fh_targets(obs, seat, day):
    """Eligible unfertilized crops, stable row-major order for reproducibility."""
    farm = obs["farms"][seat]
    out = []
    allowed = set(_FH["fh_crops"])
    for y, row in enumerate(farm.get("tiles") or []):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile.get("crop") in allowed \
                    and int(tile.get("fertilized_until_day", -1)) < day:
                out.append((x, y))
    return out

def _fh_move(pos, goal):
    """One legal board-bounded Manhattan move; LOCKED cells are walkable."""
    x, y = int(pos[0]), int(pos[1]); gx, gy = goal
    if x < gx: return ["EAST"]
    if x > gx: return ["WEST"]
    if y < gy: return ["SOUTH"]
    if y > gy: return ["NORTH"]
    return ["PASS"]

def _fh_non_sale_purchase(orders):
    """A conservative affordability contract: do not add a hire beside a buy."""
    return any(o and o[0] in ("BUY_LAND", "BUY_ANIMAL", "BUY_PRODUCT", "BUY_SEED") for o in orders)

def _fh_reset(st, day):
    st.clear(); st.update(day=day, pending=None, index=None, disabled=False)

_FH_PARENT = agent
del agent

def agent(obs, config=None):
    action = _FH_PARENT(obs, config)
    if not _FH.get("fh_on"):
        return action
    try:
        step = int(obs["step"]); day = step // 24; seat = int(obs["player"])
        st = _FH_STATE.setdefault(seat, {})
        if st.get("day") != day:
            _fh_reset(st, day)  # all hands are dismissed nightly; never retain an index.
        if not (int(_FH["fh_day0"]) <= day <= int(_FH["fh_day1"])) or step >= 696:
            return action
        farm = obs["farms"][seat]; private = obs.get("private") or {}
        hands = list(farm.get("hands") or [])
        invs = list(private.get("inventories") or [])

        # A HIRE materialises before the next observation.  We control only the
        # exact appended index; anything else means another layer changed the
        # sequence, so abstain for this day rather than touching a tape hand.
        pending = st.get("pending")
        if pending is not None:
            if len(hands) == pending + 1 and len(invs) >= pending + 2:
                st["index"] = pending; st["pending"] = None
            else:
                st["disabled"] = True; st["pending"] = None; _FH_STATS["spawn_mismatch"] += 1
        if st.get("disabled"):
            return action

        targets = _fh_targets(obs, seat, day)
        if len(targets) < int(_FH["fh_min_targets"]):
            return action
        index = st.get("index")
        if index is None:
            orders = [list(o) for o in (action.get("market") or [])]
            cost = _fh_fib(int(farm.get("hires_today", 0)))
            # Preserve all existing unit/tape commands and market priority.  A
            # late HIRE is allowed only in an unused slot, with no simultaneous
            # buy and with cash that covers the exact Fibonacci cost + reserve.
            if (len(orders) >= 10 or any(o and o[0] == "HIRE" for o in orders)
                    or _fh_non_sale_purchase(orders)
                    or float(farm.get("money", 0)) < cost + float(_FH["fh_cash_buffer"])
                    or int((private.get("shed") or {}).get("FERTILIZER", 0)) < int(_FH["fh_take"])):
                _FH_STATS["skips"] += 1
                return action
            _FH_STATS["hire_attempts"] += 1
            orders.append(["HIRE"])
            st["pending"] = len(hands)
            _FH_STATS["hires"] += 1
            return dict(action, market=orders)

        if index >= len(hands) or index + 1 >= len(invs):
            st["disabled"] = True; _FH_STATS["spawn_mismatch"] += 1
            return action
        command = None
        pos = hands[index]
        inv = invs[index + 1] or {}
        has_fert = int(inv.get("FERTILIZER", 0)) > 0
        if has_fert:
            # Prefer the tile occupied by the appended hand.  Otherwise choose
            # nearest target with a deterministic coordinate tie-break.
            target = min(targets, key=lambda q: (abs(q[0] - pos[0]) + abs(q[1] - pos[1]), q[1], q[0]))
            if tuple(pos) == target:
                command = ["FERTILIZE"]; _FH_STATS["fertilize"] += 1
            else:
                command = _fh_move(pos, target); _FH_STATS["moves"] += command != ["PASS"]
        else:
            shed = private.get("shed") or {}
            if int(shed.get("FERTILIZER", 0)) <= 0:
                return action
            access = min(_FH_ACCESS, key=lambda q: (abs(q[0] - pos[0]) + abs(q[1] - pos[1]), q[1], q[0]))
            if tuple(pos) == access:
                command = ["PICKUP", "FERTILIZER", min(int(_FH["fh_take"]), int(shed.get("FERTILIZER", 0)))]
                _FH_STATS["pickup"] += 1
            else:
                command = _fh_move(pos, access); _FH_STATS["moves"] += command != ["PASS"]
        if command is None:
            return action
        commands = [list(c) for c in (action.get("hands") or [])]
        # The base action must describe exactly the observed hands.  Do not pad
        # or truncate it: that would alter existing tape indices.
        if len(commands) != len(hands):
            st["disabled"] = True; _FH_STATS["spawn_mismatch"] += 1
            return action
        commands[index] = command
        return dict(action, hands=commands)
    except Exception:
        _FH_STATS["skips"] += 1
        return action
'''


def normalise(genes: dict[str, Any] | None) -> dict[str, Any]:
    if genes is None:
        genes = {}
    if not isinstance(genes, dict):
        raise ValueError("genes must be a dict")
    unknown = set(genes) - set(DEFAULT)
    if unknown:
        raise ValueError(f"unknown fertilizer-hand genes: {sorted(unknown)}")
    value = dict(DEFAULT)
    value.update(genes)
    if type(value["fh_on"]) is not bool:
        raise ValueError("fh_on must be bool")
    if not all(type(value[key]) is int for key in ("fh_day0", "fh_day1", "fh_min_targets", "fh_take", "fh_cash_buffer")):
        raise ValueError("fertilizer-hand numeric genes must be integers")
    if not (0 <= value["fh_day0"] <= value["fh_day1"] <= 28):
        raise ValueError("day window must be within 0..28")
    if not (1 <= value["fh_min_targets"] <= 10 and 1 <= value["fh_take"] <= 8 and value["fh_cash_buffer"] >= 0):
        raise ValueError("invalid fertilizer-hand bounds")
    if not isinstance(value["fh_crops"], list) or not value["fh_crops"] or any(x not in {"STRAWBERRY", "TOMATO"} for x in value["fh_crops"]):
        raise ValueError("fh_crops must be a nonempty subset of STRAWBERRY/TOMATO")
    return value


def build(base_main_py: str | pathlib.Path, genes: dict[str, Any] | None, out_main_py: str | pathlib.Path) -> dict[str, Any]:
    """Append the capability after a base or a previously built Horizon+ agent."""
    g = normalise(genes)
    base = pathlib.Path(base_main_py)
    out = pathlib.Path(out_main_py)
    text = base.read_text().rstrip() + "\n" + MODULE_SRC.replace("__FH_GENES__", repr(g))
    compile(text, str(out), "exec")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    info = {"base": str(base.resolve()), "genes": g, "default_off": not g["fh_on"]}
    out.with_suffix(out.suffix + ".fert_hand.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info
