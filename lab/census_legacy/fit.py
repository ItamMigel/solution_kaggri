"""Fidelity harness: build a genome -> run mirror episodes -> fingerprint -> score vs the
real-world target measured from Kaggle replays.

Usage:  python fit.py <name>            # fits one named target from TARGETS
        python fit.py <name> --seeds 3
"""
import json, os, sys, tempfile, statistics as st
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, "/workspace/kaggriculture")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---- real-world targets, measured from the 190-episode replay corpus -------------------
TARGETS = {
    # NB-v1: 30 episodes, 26 teams
    "nb1": {"money": 140710, "herd": (7.6, 6.3), "hands": 9.7, "quad": 3.07,
            "seeds": {"STRAWBERRY": 47, "MELON": 21, "WHEAT": 28, "CARROT": 0},
            "sells": {"STRAWBERRY": 288, "MELON": 118, "MILK": 217, "WOOL": 168,
                      "FERTILIZER": 218, "WHEAT": 815, "CARROT": 0}},
    # NB-v2: 24 episodes, 17 teams -- wool-led, sheep-heavy, carrot present
    "nb2": {"money": 123683, "herd": (5.0, 9.8), "hands": 8.4, "quad": 3.00,
            "seeds": {"STRAWBERRY": 34, "MELON": 20, "WHEAT": 35, "CARROT": 10},
            "sells": {"STRAWBERRY": 192, "MELON": 115, "MILK": 132, "WOOL": 199,
                      "FERTILIZER": 263, "WHEAT": 1061, "CARROT": 20}},
    # NB-partial lower bracket (26 episodes below the class median)
    "nblo": {"money": 78641, "herd": (5.7, 6.2), "hands": 7.3, "quad": 3.23,
             "seeds": {"STRAWBERRY": 44, "MELON": 28, "WHEAT": 29, "CARROT": 15},
             "sells": {"STRAWBERRY": 128, "MELON": 98, "MILK": 142, "WOOL": 116,
                       "FERTILIZER": 213, "WHEAT": 263, "CARROT": 25}},
    # NB-partial upper bracket (27 episodes above the class median)
    "nbhi": {"money": 111621, "herd": (5.9, 7.1), "hands": 7.9, "quad": 3.00,
             "seeds": {"STRAWBERRY": 39, "MELON": 23, "WHEAT": 31, "CARROT": 18},
             "sells": {"STRAWBERRY": 165, "MELON": 117, "MILK": 149, "WOOL": 153,
                       "FERTILIZER": 234, "WHEAT": 252, "CARROT": 23}},
}
KEYS = ["STRAWBERRY", "MELON", "MILK", "WOOL", "FERTILIZER", "WHEAT", "CARROT"]


def _one(args):
    src, seed = args
    from kaggle_environments import make
    from src.replay_mine import mine
    from fp import features
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run([src, src])
    j = env.toJSON()
    d = {"configuration": dict(j["configuration"]), "id": f"fit-{seed}",
         "info": {"seed": seed, "TeamNames": ["a", "b"]},
         "rewards": [s.get("reward") for s in j["steps"][-1]], "steps": j["steps"]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(d, f); tmp = f.name
    r = mine(tmp, verbose=False)
    os.unlink(tmp)
    fs = features(r)
    # crash check: agent stopped being called / money never moved
    crashed = any(sum(x["unit_ops"].values()) < 100 for x in fs)
    return fs + [crashed]


def evaluate(genome, seeds=(60000, 60001, 61000), workers=6):
    import importlib.util as _il
    _sp=_il.spec_from_file_location("_aa","/workspace/kaggriculture/src/animal_agent.py")
    _aa=_il.module_from_spec(_sp); _sp.loader.exec_module(_aa)
    build_source=_aa.build_source
    src = build_source(genome)
    path = tempfile.mktemp(suffix=".py")
    with open(path, "w") as f:
        f.write(src)
    try:
        with ProcessPoolExecutor(max_workers=min(workers, len(seeds))) as ex:
            out = list(ex.map(_one, [(path, s) for s in seeds]))
    finally:
        os.unlink(path)
    recs = []
    crashed = False
    for o in out:
        recs += o[:2]
        crashed = crashed or o[2]
    agg = {
        "money": st.mean(x["money"] for x in recs),
        "herd": (st.mean(x["herd"]["COW"] for x in recs), st.mean(x["herd"]["SHEEP"] for x in recs)),
        "hands": st.mean(x["hands"] for x in recs),
        "quad": st.mean(x["n_quad"] for x in recs),
        "seeds": {k: st.mean(x["seeds"].get(k, 0) for x in recs) for k in ("STRAWBERRY", "MELON", "WHEAT", "CARROT")},
        "sells": {k: st.mean(x["sells"].get(k, 0) for x in recs) for k in KEYS},
        "bpWHEAT": st.mean(x["products_bought"].get("WHEAT", 0) for x in recs),
        "crashed": crashed, "n": len(recs),
    }
    return agg


def report(name, got, tgt=None):
    tgt = tgt or TARGETS[name]
    print(f"--- {name}  (n={got['n']} mirror episodes, crashed={got['crashed']}) ---")
    print(f"  money  ${got['money']:>9,.0f}   target ${tgt['money']:>9,.0f}   fidelity {100*got['money']/tgt['money']:5.1f}%")
    print(f"  herd   {got['herd'][0]:.1f}c/{got['herd'][1]:.1f}s  target {tgt['herd'][0]:.1f}c/{tgt['herd'][1]:.1f}s   "
          f"hands {got['hands']:.1f} vs {tgt['hands']:.1f}   quad {got['quad']:.2f} vs {tgt['quad']:.2f}")
    print(f"  seeds  " + "  ".join(f"{k[:5]}={got['seeds'][k]:4.0f}/{tgt['seeds'].get(k,0):<4.0f}" for k in got["seeds"]))
    errs = []
    line = []
    for k in KEYS:
        t = tgt["sells"].get(k, 0); g = got["sells"][k]
        line.append(f"{k[:5]}={g:5.0f}/{t:<5.0f}")
        if t >= 50:
            errs.append(abs(g - t) / t)
    print(f"  sold   " + "  ".join(line))
    print(f"  bpWHEAT {got['bpWHEAT']:.0f}")
    score = 100 * (1 - st.mean(errs)) if errs else 0
    print(f"  ==> production fidelity (mean |err| over lines >=50u): {score:.1f}%")
    return score
