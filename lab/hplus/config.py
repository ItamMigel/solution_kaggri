"""Build-time M4 configuration for the frozen ``es1_g9`` source.

The Horizon chassis consumes ``_SETTINGS`` and its route/opening constants while
the source is imported.  A globals update appended at EOF is therefore too late.
This module changes only audited source anchors before import.  With the default
genes it copies the input byte-for-byte; that is the genome-zero contract.

This deliberately does *not* permit an earlier final-day takeover.  The inherited
FD planner is a terminal liquidator, not a mid-season production controller.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import re
from typing import Any


DEFAULT_GENES: dict[str, Any] = {
    "settings": {},
    "opening_qty": None,
    "router_switch_step": None,
    "fd_takeover_step": None,
}

_SETTINGS_RE = re.compile(r"(?m)^_SETTINGS=(\{[^\n]+\})$")
_R4_RE = re.compile(r"(?m)^_R4_CONFIG=(\{[^\n]+\})$")
_ROUTER_RE = "if step>=648 and not state.get('day27'):"
_FD_RE = "if step<696:return _FD_PARENT(observation,configuration)"
_ROUTE_HELPER_RE = "t >= 648"


class BuildError(ValueError):
    """The frozen source is not the version whose anchors were reviewed."""


def _literal_assignment(source: str, pattern: re.Pattern[str], name: str) -> tuple[dict[str, Any], re.Match[str]]:
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise BuildError(f"expected one {name} assignment, found {len(matches)}")
    value = ast.literal_eval(matches[0].group(1))
    if not isinstance(value, dict):
        raise BuildError(f"{name} is not a dict literal")
    return value, matches[0]


def normalise(genes: dict[str, Any] | None) -> dict[str, Any]:
    """Validate a candidate M4 genome without silently accepting typoed genes."""
    if genes is None:
        genes = {}
    if not isinstance(genes, dict):
        raise BuildError("genes must be a JSON object")
    unknown = set(genes) - set(DEFAULT_GENES)
    if unknown:
        raise BuildError(f"unknown genes: {sorted(unknown)}")
    out = dict(DEFAULT_GENES)
    out.update(genes)
    if not isinstance(out["settings"], dict):
        raise BuildError("settings must be an object")
    if out["opening_qty"] is not None and (type(out["opening_qty"]) is not int or not 5 <= out["opening_qty"] <= 30):
        raise BuildError("opening_qty must be an integer in [5, 30] or null")
    if out["router_switch_step"] is not None and (type(out["router_switch_step"]) is not int or not 600 <= out["router_switch_step"] <= 696):
        raise BuildError("router_switch_step must be an integer in [600, 696] or null")
    # The FD planner hard-codes day-29/terminal assumptions.  Delaying it is an
    # auditable terminal ablation; starting it early is not an M4 capability.
    if out["fd_takeover_step"] is not None and (type(out["fd_takeover_step"]) is not int or not 696 <= out["fd_takeover_step"] <= 718):
        raise BuildError("fd_takeover_step must be an integer in [696, 718] or null")
    return out


def build_text(source: str, genes: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    """Return configured source and canonical genes; defaults preserve source bytes."""
    g = normalise(genes)
    if g == DEFAULT_GENES:
        return source, g

    text = source
    if g["settings"]:
        current, match = _literal_assignment(text, _SETTINGS_RE, "_SETTINGS")
        invalid = set(g["settings"]) - set(current)
        if invalid:
            raise BuildError(f"unknown _SETTINGS keys: {sorted(invalid)}")
        if any(type(v) is not bool for v in g["settings"].values()):
            raise BuildError("_SETTINGS values must be booleans")
        current.update(g["settings"])
        text = text[:match.start(1)] + repr(current) + text[match.end(1):]

    if g["opening_qty"] is not None:
        current, match = _literal_assignment(text, _R4_RE, "_R4_CONFIG")
        if set(current) != {"opening"} or type(current["opening"]) is not int:
            raise BuildError("unexpected final opening config")
        current["opening"] = g["opening_qty"]
        text = text[:match.start(1)] + repr(current) + text[match.end(1):]

    if g["router_switch_step"] is not None:
        if text.count(_ROUTER_RE) != 1:
            raise BuildError("router switch anchor changed")
        # Future-tape consumers must agree with the live router or their market
        # reservations are computed from a different tape.
        helper_count = text.count(_ROUTE_HELPER_RE)
        if helper_count != 7:
            raise BuildError(f"expected 7 route helper anchors, found {helper_count}")
        step = g["router_switch_step"]
        text = text.replace(_ROUTER_RE, f"if step>={step} and not state.get('day27'):")
        text = text.replace(_ROUTE_HELPER_RE, f"t >= {step}")

    if g["fd_takeover_step"] is not None:
        if text.count(_FD_RE) != 1:
            raise BuildError("FD takeover anchor changed")
        text = text.replace(_FD_RE, f"if step<{g['fd_takeover_step']}:return _FD_PARENT(observation,configuration)")

    try:
        compile(text, "configured_horizon.py", "exec")
    except SyntaxError as exc:  # pragma: no cover - defensive source gate
        raise BuildError(f"generated source does not compile: {exc}") from exc
    return text, g


def build(base_main_py: str | pathlib.Path, genes: dict[str, Any] | None, out_main_py: str | pathlib.Path) -> dict[str, Any]:
    """Write a self-contained configured agent and a JSON sidecar with its digest."""
    base = pathlib.Path(base_main_py)
    out = pathlib.Path(out_main_py)
    source = base.read_text()
    text, canonical = build_text(source, genes)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    info = {
        "base": str(base.resolve()),
        "base_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "genes": canonical,
        "output_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "genome_zero_byte_identical": text == source,
    }
    out.with_suffix(out.suffix + ".build.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n")
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--genes", required=True, help="JSON file or inline JSON object")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    candidate = pathlib.Path(args.genes)
    raw = candidate.read_text() if candidate.is_file() else args.genes
    print(json.dumps(build(args.base, json.loads(raw), args.out), indent=2))


if __name__ == "__main__":
    main()
