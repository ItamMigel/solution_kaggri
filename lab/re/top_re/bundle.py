"""Bundle plan.py + market.py + units.py + main_src.py into one self-contained main.py (Kaggle loader takes the LAST callable)."""
import os, sys
H = os.path.dirname(os.path.abspath(__file__)); out = sys.argv[1] if len(sys.argv) > 1 else f"{H}/main.py"
parts = []
import json
PLAN = os.environ.get("TOPRE_PLAN", "plan")
fm_json = open("/workspace/shared/research/re/fm_top_model.json").read() if PLAN == "plan_fm" else None
mpc2_json = open(os.environ.get("TOPRE_MODEL", "/workspace/shared/research/re/models.json")).read() if PLAN == "plan_mpc2" else None
for mod, exports in ((PLAN, {"desired": "plan_desired", "targets": "plan_targets"}), ("market", {"orders": "market_orders"}), ("units", {"act": "units_act"})):
    src = open(f"{H}/{mod}.py").read()
    if mod == "plan_fm": src = src.replace("FM = None  # filled by bundle (FM_MODEL json)", "FM = " + repr(json.loads(fm_json)))
    if mod == "plan_mpc2": src = src.replace("MPC2 = None  # filled by bundle (TOPRE_MODEL json)", "MPC2 = " + repr(json.loads(mpc2_json)))
    parts.append(f"_{mod.upper()}_NS = {{}}\nexec(compile({src!r}, '{mod}.py', 'exec'), _{mod.upper()}_NS)\n" +
                 "".join(f"{alias} = _{mod.upper()}_NS[{name!r}]\n" for name, alias in exports.items()))
parts.append(open(f"{H}/main_src.py").read())
open(out, "w").write("\n".join(parts)); print("wrote", out)
