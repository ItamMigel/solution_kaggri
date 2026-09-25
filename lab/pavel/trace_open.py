"""Step-by-step trace of the opening: BC agent (closed loop) vs recorded expert in the same world.
usage: python trace_open.py --ckpt ... --replay ... --team Boey --steps 0-40 [--persist] [--msample]"""
import argparse, contextlib, gzip, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "bc3"))


def short_u(a):
    if not a: return "-"
    if a[0] in ("PICKUP", "PLACE"): return f"{a[0][:2]}{a[1][:3]}{a[2] if len(a) > 2 else ''}"
    if a[0] == "PLANT": return f"PL{a[1][:3]}"
    return {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W"}.get(a[0], a[0][:5])


def short_m(o):
    if not o: return "-"
    if o[0] in ("HIRE", "BUY_LAND", "NOOP"): return o[0][:4]
    return {"SELL": "S", "BUY_PRODUCT": "B", "BUY_SEED": "Sd", "BUY_ANIMAL": "A"}.get(o[0], o[0]) + ":" + o[1][:3] + str(o[2] if len(o) > 2 else "")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ckpt", required=True); ap.add_argument("--replay", required=True)
    ap.add_argument("--team", required=True); ap.add_argument("--steps", default="0-40"); ap.add_argument("--persist", action="store_true")
    ap.add_argument("--msample", action="store_true")
    a = ap.parse_args()
    from kaggle_environments import make
    import agent3
    d = json.load(gzip.open(a.replay, "rt")); names = d["info"]["TeamNames"]; p = names.index(a.team)
    tapes = [[d["steps"][k + 1][s]["action"] for k in range(len(d["steps"]) - 1)] for s in (0, 1)]
    cfg = {k: v for k, v in d["configuration"].items() if k not in ("agents", "seed")}; cfg["seed"] = d["info"]["seed"]
    bc = agent3.Agent(os.path.abspath(a.ckpt), persist=a.persist, msample=a.msample)
    lo, hi = [int(x) for x in a.steps.split("-")]

    def opp(obs, config=None):
        k = int(obs.get("step", 0)); return tapes[1 - p][k] if k < len(tapes[1 - p]) else {}
    agents = [bc, opp] if p == 0 else [opp, bc]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        env = make("kaggriculture", configuration=cfg, debug=False); env.run(agents)
    for t in range(lo, hi + 1):
        ob = env.steps[t][0].observation; f = ob["farms"][p]; priv = env.steps[t][p].observation["private"]
        ro = d["steps"][t][0]["observation"]; rf = ro["farms"][p]; rpriv = d["steps"][t][p]["observation"]["private"]
        sa = env.steps[t + 1][p].action or {}; ra = d["steps"][t + 1][p]["action"] or {}
        shed = {k[:3]: v for k, v in priv["shed"].items() if v}; rshed = {k[:3]: v for k, v in rpriv["shed"].items() if v}
        print(f"t={t:3} h={t % 24:2} BC ${round(f['money'])} shed{shed} inv{[{k[:3]: v for k, v in i.items() if v} for i in priv['inventories']]}")
        print(f"        BC  units: {' '.join(short_u(u) for u in [sa.get('farmer')] + list(sa.get('hands') or []))} | mkt: {' '.join(short_m(o) for o in sa.get('market') or [])}")
        print(f"      EXP ${round(rf['money'])} shed{rshed} units: {' '.join(short_u(u) for u in [ra.get('farmer')] + list(ra.get('hands') or []))} | mkt: {' '.join(short_m(o) for o in ra.get('market') or [])}")


if __name__ == "__main__":
    main()
