"""Bundle plan.py + market.py + units.py + main_src.py into one self-contained main.py (Kaggle loader takes the LAST callable)."""
import os, sys
H = os.path.dirname(os.path.abspath(__file__)); out = sys.argv[1] if len(sys.argv) > 1 else f"{H}/main.py"
parts = []
for mod, exports in (("plan", {"desired": "plan_desired", "targets": "plan_targets"}), ("market", {"orders": "market_orders"}), ("units", {"act": "units_act"})):
    src = open(f"{H}/{mod}.py").read()
    parts.append(f"_{mod.upper()}_NS = {{}}\nexec(compile({src!r}, '{mod}.py', 'exec'), _{mod.upper()}_NS)\n" +
                 "".join(f"{alias} = _{mod.upper()}_NS[{name!r}]\n" for name, alias in exports.items()))
parts.append(open(f"{H}/main_src.py").read())
open(out, "w").write("\n".join(parts)); print("wrote", out)
