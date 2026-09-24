from __future__ import annotations
import contextlib, copy, hashlib, importlib.metadata, inspect, io, json, sys
from pathlib import Path
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from kaggle_environments.agent import get_last_callable
    from kaggle_environments.envs.kaggriculture import kaggriculture as engine
from typing import Any
from numbers import Integral

ALLOWED_ACTION_KEYS = frozenset({"farmer", "hands", "market"})

FIELD_NO_ARGUMENT_OPS = frozenset(
    {
        "NORTH",
        "SOUTH",
        "EAST",
        "WEST",
        "PASS",
        "DROP",
        "WATER",
        "HARVEST",
        "FERTILIZE",
        "BUILD_COOP",
        "BUILD_PASTURE",
        "FEED",
        "COLLECT_FERTILIZER",
        "CARE",
        "DIG",
    }
)

CROPS = frozenset({"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"})

ANIMALS = frozenset({"GOOSE", "COW", "SHEEP"})

PRODUCTS = frozenset(
    {
        "WHEAT",
        "CARROT",
        "TOMATO",
        "STRAWBERRY",
        "MELON",
        "EGG",
        "MILK",
        "WOOL",
        "FERTILIZER",
    }
)

class KaggleAgentContractError(ValueError):
    """Raised when local agent semantics differ from Kaggle deployment."""

def require_action_mapping(action: Any) -> dict[str, Any]:
    """Reject values that Kaggriculture would silently reduce to no-ops."""

    # The pinned environment checks ``isinstance(action, dict)`` before
    # reading channels.  A generic Mapping would otherwise pass locally here
    # and become a silent all-PASS action in competition execution.
    if not isinstance(action, dict):
        raise KaggleAgentContractError(
            "Kaggriculture agent action must be a mapping, got "
            f"{type(action).__name__}"
        )
    unknown = set(action) - ALLOWED_ACTION_KEYS
    if unknown:
        raise KaggleAgentContractError(
            f"Kaggriculture action contains unknown keys: {sorted(unknown)}"
        )
    return action

def require_strict_action_contract(
    action: Any,
    *,
    expected_hands: int | None = None,
    max_market_orders: int = 10,
) -> dict[str, Any]:
    """Validate the complete action shape required of release candidates."""

    action = require_action_mapping(action)
    if set(action) != ALLOWED_ACTION_KEYS:
        raise KaggleAgentContractError(
            "release action must contain exactly farmer, hands, and market"
        )
    farmer = action["farmer"]
    hands = action["hands"]
    market = action["market"]
    if not isinstance(farmer, list) or not farmer:
        raise KaggleAgentContractError("farmer action must be a non-empty list")
    if not isinstance(hands, list):
        raise KaggleAgentContractError("hands actions must be a list")
    if not isinstance(market, list):
        raise KaggleAgentContractError("market actions must be a list")
    if expected_hands is not None and len(hands) != int(expected_hands):
        raise KaggleAgentContractError(
            f"hands action count {len(hands)} != observed hands {expected_hands}"
        )
    if len(market) > int(max_market_orders):
        raise KaggleAgentContractError(
            f"market action count {len(market)} exceeds cap {max_market_orders}"
        )
    _require_field_action(farmer, channel="farmer")
    for index, hand_action in enumerate(hands):
        _require_field_action(hand_action, channel=f"hands[{index}]")
    for index, order in enumerate(market):
        _require_market_action(order, index=index)
    return action

def _is_positive_integer(value: Any) -> bool:
    return isinstance(value, Integral) and not isinstance(value, bool) and value > 0

def _require_field_action(action: Any, *, channel: str) -> None:
    if not isinstance(action, list) or not action or not isinstance(action[0], str):
        raise KaggleAgentContractError(f"{channel} must be a non-empty action list")
    op = action[0]
    if op in FIELD_NO_ARGUMENT_OPS:
        if len(action) != 1:
            raise KaggleAgentContractError(
                f"{channel} operation {op} takes no arguments"
            )
        return
    if op == "PLANT":
        if len(action) != 2 or action[1] not in CROPS:
            raise KaggleAgentContractError(
                f"{channel} PLANT requires exactly one valid crop"
            )
        return
    if op in {"PICKUP", "PLACE"}:
        if len(action) not in {2, 3} or not isinstance(action[1], str):
            raise KaggleAgentContractError(
                f"{channel} {op} requires an item and optional positive quantity"
            )
        if action[1] not in PRODUCTS | ANIMALS:
            raise KaggleAgentContractError(f"{channel} {op} has unknown item")
        if len(action) == 3 and not _is_positive_integer(action[2]):
            raise KaggleAgentContractError(
                f"{channel} {op} quantity must be a positive integer"
            )
        return
    raise KaggleAgentContractError(f"{channel} has unknown operation {op!r}")

def _require_market_action(order: Any, *, index: int) -> None:
    channel = f"market[{index}]"
    if not isinstance(order, list) or not order or not isinstance(order[0], str):
        raise KaggleAgentContractError(f"{channel} must be a non-empty order list")
    op = order[0]
    if op in {"HIRE", "BUY_LAND"}:
        if len(order) != 1:
            raise KaggleAgentContractError(
                f"{channel} operation {op} takes no arguments"
            )
        return
    if op not in {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}:
        raise KaggleAgentContractError(f"{channel} has unknown operation {op!r}")
    if len(order) != 3 or not _is_positive_integer(order[2]):
        raise KaggleAgentContractError(
            f"{channel} requires item and positive integer quantity"
        )
    item = order[1]
    valid_items = {
        "BUY_SEED": CROPS,
        "BUY_PRODUCT": frozenset({"WHEAT", "FERTILIZER"}),
        "BUY_ANIMAL": ANIMALS,
        "SELL": PRODUCTS,
    }[op]
    if item not in valid_items:
        raise KaggleAgentContractError(f"{channel} {op} has invalid item {item!r}")

def scoped_action_profile(action, *, expected_hands=None, max_market_orders=10):
    """Keep exact no-op slots; validate every effective order with the strict contract."""
    try:
        require_strict_action_contract(action, expected_hands=expected_hands,
                                       max_market_orders=max_market_orders)
        strict_pass = True
    except KaggleAgentContractError:
        strict_pass = False
    if not isinstance(action, dict) or not isinstance(action.get("market"), list):
        raise KaggleAgentContractError("invalid candidate action mapping or market")
    if len(action["market"]) > max_market_orders:
        raise KaggleAgentContractError("market slot cap exceeded")
    placeholders = sum(order == ["SELL", "WHEAT", 0] and type(order[-1]) is int
                       for order in action["market"])
    effective = [order for order in action["market"]
                 if not (order == ["SELL", "WHEAT", 0] and type(order[-1]) is int)]
    require_strict_action_contract(dict(action, market=effective), expected_hands=expected_hands,
                                   max_market_orders=max_market_orders)
    return {"canonical_strict_pass": strict_pass, "engine_noop_slot_profile_pass": True,
            "preserved_noop_slots": placeholders}

PINS = {'package_version': '1.32.7', 'loader_sha256': '89a04abd3e8cebac273fdc810a3c933301143821bf354aeb4d460322921c487c', 'engine_sha256': 'bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e', 'schema_sha256': 'a82c89c1a2315b93f39775d8e025471a01b738647c9772658368ee6b1b6f4867'}
runtime, fixture_path, receipt_path = map(Path, sys.argv[1:])
engine_path = Path(inspect.getsourcefile(engine))
actual = {
    "package_version": importlib.metadata.version("kaggle-environments"),
    "loader_sha256": hashlib.sha256(inspect.getsource(get_last_callable).encode()).hexdigest(),
    "engine_sha256": hashlib.sha256(engine_path.read_bytes()).hexdigest(),
    "schema_sha256": hashlib.sha256(engine_path.with_name("kaggriculture.json").read_bytes()).hexdigest(),
}
if actual != PINS:
    raise RuntimeError("installed engine, schema, or official loader differs from the pinned contract")
fixture = json.loads(fixture_path.read_text())
entrypoint = runtime / "main.py"
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    selected = get_last_callable(entrypoint.read_text(), path=str(entrypoint))
    if selected.__name__ != "agent" or selected.__globals__.get("agent") is not selected:
        raise RuntimeError("official loader did not select the exact agent binding")
    observation = copy.deepcopy(fixture["observation"])
    configuration = copy.deepcopy(fixture["configuration"])
    configuration["__raw_path__"] = str(entrypoint)
    arguments = [observation, configuration]
    code = getattr(selected, "__code__", None)
    if code is not None and hasattr(code, "co_argcount"):
        arguments = arguments[:code.co_argcount]
    action = selected(*arguments)
action_json = json.dumps(action, sort_keys=True, separators=(",", ":"), allow_nan=False)
if len(action_json.encode()) > 1_000_000:
    raise RuntimeError("action exceeds byte limit")
action = json.loads(action_json)
hands = len(fixture["observation"]["farms"][int(fixture["observation"]["player"])]["hands"])
checks = scoped_action_profile(action, expected_hands=hands,
    max_market_orders=fixture["configuration"].get("maxMarketOrdersPerTurn", 10))
telemetry = copy.deepcopy(getattr(selected, "telemetry", {}))
if telemetry.get("admission_errors", 0):
    raise RuntimeError("admission module reported an internal error")
upstream_errors = {name: count for name, count in telemetry.get("upstream_error_counters", {}).items()
                   if "error" in name.lower() and count != 0}
if upstream_errors:
    raise RuntimeError("upstream reported internal errors: " + json.dumps(upstream_errors, sort_keys=True))
fallback_counters = {name: count for name, count in telemetry.get("upstream_error_counters", {}).items()
                     if "fallback" in name.lower() and "error" not in name.lower()}
receipt = {
    "artifact_type": "candidate_initial_observation_smoke", "engine": actual,
    "official_loader_selected": selected.__name__, "exact_agent_binding": True,
    "action_checks": checks, "observation_calls": 1, "full_games": 0,
    "seed_allocations": 0, "action": action,
    "action_sha256": hashlib.sha256(action_json.encode()).hexdigest(),
    "fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
    "entrypoint_sha256": hashlib.sha256(entrypoint.read_bytes()).hexdigest(),
    "telemetry": telemetry,
    "nonzero_upstream_errors": upstream_errors,
    "ordinary_fallback_counters_informational": fallback_counters,
    "provenance": fixture["provenance"],
    "scope": "Initial off-policy observation only. No score, branch reachability, or performance claim.",
}
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
