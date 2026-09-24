"""Tunable-knob interface for Horizon v5 (shared by ES [claude] and PPO [codex]).
make_agent_file(params, out) writes a self-contained main.py = horizon_v5_market + globals override appended.
Module-level knobs are looked up by the functions at call time, so an override at the end of the file takes effect."""
import json, os
BASE = "/workspace/wt/claude/agents/horizon_v5_market.py"
# name: (base, lo, hi, kind)
SPACE = {
    "_ADV_LOOK": (12, 4, 20, "int"),
    "_V92_P_H": (48, 12, 96, "int"),
    "_V92_P_K": (4, 1, 8, "int"),
    "_V92_Q_H": (48, 12, 96, "int"),
    "_V92_Q_PF": (1.0, 0.3, 2.0, "float"),
    "_V92_Q_PM": (0.5, 0.0, 1.5, "float"),
    "_CA_MARGIN": (-5.0, -40.0, 30.0, "float"),
    "_CA_BUFFER": (8, 0, 30, "int"),
    "_CA_CASH": (800, 0, 3000, "int"),
    "_OR2_CAP": (30, 5, 80, "int"),
    "_OR2_SLOT_MARGIN": (20.0, 0.0, 60.0, "float"),
    "_CH_SHED": (90, 50, 100, "int"),
    "_SR_MARGIN": (8, 0, 30, "int"),
    "_HD2_RATIO": (1.3, 0.8, 2.5, "float"),
    "_HD2_MIN_GAIN": (600.0, 0.0, 3000.0, "float"),
    "_HD2_CARE": (0.8, 0.3, 1.2, "float"),
    "_CS_RATIO": (1.3, 0.8, 2.5, "float"),
    "_CS_MIN_GAIN": (600.0, 0.0, 3000.0, "float"),
    "_RACE_HORIZON_CLONE": (9, 3, 24, "int"),
    "_RACE_HORIZON_ESCALATED": (24, 8, 48, "int"),
    "_Y_MARGIN": (-6, -40, 30, "int"),
    "_FD_POWER": (0.7, 0.3, 1.2, "float"),
    "_FD_WIDTH": (8, 4, 16, "int"),
    "_HH_MARGIN": (2.0, 0.0, 10.0, "float"),
}

def clip(name, v):
    b, lo, hi, k = SPACE[name]
    v = min(hi, max(lo, v))
    return int(round(v)) if k == "int" else float(v)

def base_params():
    return {k: v[0] for k, v in SPACE.items()}

def make_agent_file(params, out, base=BASE):
    src = open(base).read().rstrip() + "\n"
    ov = {k: clip(k, v) for k, v in params.items()}
    src += "\n# --- knobs override (lab/tools/knobs.py) ---\nglobals().update(" + json.dumps(ov) + ")\n"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write(src)
    return ov
