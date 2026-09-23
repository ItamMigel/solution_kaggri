"""Fidelity of our four frontier imitations against the FRESH (2026-08-04) ladder fingerprints,
on BOTH axes: money and physical production.

Two conditions, because the ladder fingerprint was measured while the real opponent played
*against us*, not against a copy of itself:
  mirror   : imitation vs imitation      (comparable with the 2026-08-03 fidelity numbers)
  vs_champ : imitation vs best_exp032.py (the condition the real fingerprints were measured in)

Usage: python fit2.py [--seeds N] [--champ path]
"""
import argparse, json, os, statistics as st, sys, tempfile
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/workspace/kaggriculture")
sys.path.insert(0, HERE)

KEYS = ["STRAWBERRY", "MELON", "MILK", "WOOL", "FERTILIZER", "WHEAT", "CARROT"]
POOL = "/workspace/kaggriculture/artifacts/agents/pool"


def _one(args):
    """(srcA, srcB, seed) -> (featuresA, featuresB) ; A is the imitation."""
    a, b, seed = args
    from kaggle_environments import make
    from src.replay_mine import mine
    from fp import features
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run([a, b])
    j = env.toJSON()
    d = {"configuration": dict(j["configuration"]), "id": f"fit2-{seed}",
         "info": {"seed": seed, "TeamNames": ["A", "B"]},
         "rewards": [s.get("reward") for s in j["steps"][-1]], "steps": j["steps"]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(d, f)
        tmp = f.name
    try:
        r = mine(tmp, verbose=False)
    finally:
        os.unlink(tmp)
    return features(r)


def agg(recs):
    g = lambda fn: st.mean(fn(x) for x in recs)  # noqa: E731
    return {"n": len(recs), "money": g(lambda x: x["money"]),
            "cow": g(lambda x: x["herd"]["COW"]), "sheep": g(lambda x: x["herd"]["SHEEP"]),
            "hands": g(lambda x: x["hands"]), "quad": g(lambda x: x["n_quad"]),
            "seeds": {k: g(lambda x, k=k: x["seeds"].get(k, 0)) for k in ("STRAWBERRY", "MELON", "WHEAT", "CARROT")},
            "sells": {k: g(lambda x, k=k: x["sells"].get(k, 0)) for k in KEYS},
            "bpWHEAT": g(lambda x: x["products_bought"].get("WHEAT", 0)),
            "crashed": any(sum(x["unit_ops"].values()) < 100 for x in recs)}


def score(got, tgt):
    """money fidelity + production fidelity (mean |rel err| over lines with target >= 50u).

    Reported twice: with WHEAT (comparable with the 2026-08-03 numbers) and without it. The
    wheat run is a DELIBERATE non-copy -- measured at -$11,649 net for the notebooks -- so
    including it scores us down for a decision that was taken on evidence.
    """
    def _p(keys):
        errs = [abs(got["sells"][k] - tgt["sells"][k]) / tgt["sells"][k]
                for k in keys if tgt["sells"].get(k, 0) >= 50]
        return 100 * (1 - st.mean(errs)) if errs else float("nan")
    return 100 * got["money"] / tgt["money"], _p(KEYS), _p([k for k in KEYS if k != "WHEAT"])


def show(name, cond, got, tgt):
    m, p, pnw = score(got, tgt)
    print(f"  [{cond:8s}] n={got['n']:2d} money ${got['money']:>8,.0f} / ${tgt['money']:>8,.0f} = {m:5.1f}%   "
          f"production = {p:5.1f}% (без пшеницы {pnw:5.1f}%)   crashed={got['crashed']}")
    print(f"             herd {got['cow']:.1f}c/{got['sheep']:.1f}s vs {tgt['cow']:.1f}c/{tgt['sheep']:.1f}s  "
          f"hands {got['hands']:.1f}/{tgt['hands']:.1f}  quad {got['quad']:.2f}/{tgt['quad']:.2f}  "
          f"bpW {got['bpWHEAT']:.0f}/{tgt['bpWHEAT']:.0f}")
    print("             sold  " + "  ".join(
        f"{k[:5]}={got['sells'][k]:5.0f}/{tgt['sells'].get(k,0):<5.0f}" for k in KEYS))
    return m, p, pnw


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--champ", default="/workspace/kaggriculture/artifacts/agents/best_exp032.py")
    ap.add_argument("--targets", default=os.path.join(HERE, "targets_new.json"))
    ap.add_argument("--cores", type=int, default=12)
    ap.add_argument("--out", default=os.path.join(HERE, "fit2_out.json"))
    a = ap.parse_args()

    targets = json.load(open(a.targets))     # {name: {imit: <pool file>, old: {...}, new: {...}}}
    tasks, meta = [], []
    for name, spec in targets.items():
        imit = os.path.join(POOL, spec["imit"])
        for i in range(a.seeds):
            tasks.append((imit, a.champ, 70000 + i)); meta.append((name, "vs_champ", 0))
            tasks.append((a.champ, imit, 70000 + i)); meta.append((name, "vs_champ", 1))
        for i in range(max(2, a.seeds // 2)):
            tasks.append((imit, imit, 71000 + i)); meta.append((name, "mirror", 0))

    with ProcessPoolExecutor(max_workers=a.cores) as ex:
        res = list(ex.map(_one, tasks, chunksize=1))

    buckets = {}
    for (name, cond, side), fs in zip(meta, res):
        buckets.setdefault((name, cond), []).append(fs[side])

    out = {}
    for name, spec in targets.items():
        print(f"\n=== {name}  ({spec['imit']}) ===")
        for cond in ("vs_champ", "mirror"):
            recs = buckets.get((name, cond))
            if not recs:
                continue
            got = agg(recs)
            for era in ("new", "old"):
                if era in spec:
                    print(f"   target={era.upper()} corpus")
                    m, p, pnw = show(name, cond, got, spec[era])
                    out[f"{name}|{cond}|{era}"] = {"money_fid": m, "prod_fid": p,
                                                   "prod_fid_nowheat": pnw, "got": got}
    json.dump(out, open(a.out, "w"), indent=1, default=float)
    print("\nwrote", a.out)
