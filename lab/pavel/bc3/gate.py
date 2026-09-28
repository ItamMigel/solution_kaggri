"""Selection gate for BC candidates: a broad panel (Horizon family, Adil's es2_c1, public controllers, the submitted v1)
on confirmation worlds, both seats. Prints per-opponent score and the panel mean; a new candidate must beat v1 on the
panel mean AND not lose head-to-head to v1.
usage: python gate.py --agent NAME=path/main.py [--agent ...] --worlds 64 --workers 40 --out ../../../../runs/compare/gate_x"""
import argparse, json, os, subprocess, sys

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[_v] = "1"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SOL = os.path.join(ROOT, "solution"); PY = os.path.join(ROOT, ".venv", "bin", "python")
POOL = os.path.join(ROOT, "adil-board", "opponents", "pool")
OPPONENTS = {
    "es2c1": os.path.join(ROOT, "adil-board", "candidates", "es2_c1", "pkg", "main.py"),
    "v1": os.path.join(ROOT, "candidates", "bc3_m5ens_mg_v1", "main.py"),
    "metav4": os.path.join(POOL, "tschinkel_metav4_v13", "main.py"),
    "t2945": os.path.join(POOL, "tschinkel2945", "main.py"),
    "ozer45": os.path.join(POOL, "ozer_v45", "main.py"),
    "parthenos": os.path.join(POOL, "parthenos_robust", "main.py"),
    "yhay0913": os.path.join(POOL, "yhay_router0913", "main.py"),
    "fukami": os.path.join(POOL, "fukami_v48", "main.py"),
}
BASELINES = ["v5_market", "v4_12turn"]
CAND = os.path.join(ROOT, "adil-board", "candidates"); PUB = os.path.join(ROOT, "research", "public", "agents")
# "field" panel (2026-09-28): the current Horizon-lineage field — strongest public agent, our ladder candidates, old and new
# public clones, a weak non-clone and a BC agent as a stand-in for reactive (own-route) top agents
FIELD = {
    "tetsu": os.path.join(ROOT, "research", "public_tmp", "tetsu1009", "main.py"),
    "es7": os.path.join(CAND, "es7_wm", "pkg", "main.py"), "es3": os.path.join(CAND, "es3_g5", "pkg", "main.py"),
    "es6": os.path.join(CAND, "es6_c4g15", "pkg", "main.py"), "es1g1": os.path.join(CAND, "es1_g1", "pkg", "main.py"),
    "metav4": os.path.join(POOL, "tschinkel_metav4_v13", "main.py"), "parthenos": os.path.join(POOL, "parthenos_robust", "main.py"),
    "yhay0913": os.path.join(POOL, "yhay_router0913", "main.py"),
    "harvest": os.path.join(PUB, "haodou092__kaggriculture-harvest-ledger", "main.py"),
    "ozer55": os.path.join(PUB, "ahmedberatozer__kaggriculture-v55-one-turn-market-race-edge", "main.py"),
    "v57": os.path.join(PUB, "nihilisticneuralnet__kaggriculture-population-robust-economy", "main.py"),
    "fukami": os.path.join(POOL, "fukami_v48", "main.py"),
    "bc_m15s0": os.path.join(ROOT, "runs", "agents", "np_m15s0_mg", "main.py"),
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--agent", action="append", required=True)
    ap.add_argument("--worlds", type=int, default=64); ap.add_argument("--workers", type=int, default=40)
    ap.add_argument("--out", required=True); ap.add_argument("--skip", default="", help="comma list of opponents to skip")
    ap.add_argument("--panel", default="bc", choices=["bc", "field"], help="bc: 2026-09-25 BC gate; field: current Horizon-lineage field")
    a = ap.parse_args()
    conf = json.load(open(os.path.join(SOL, "seeds", "confirmation.json")))
    sf = os.path.join(ROOT, "runs", "compare", f"conf{a.worlds}.json")
    json.dump(dict(conf, seeds=conf["seeds"][: a.worlds], purpose=f"confirmation first {a.worlds}"), open(sf, "w"))
    skip = set(x for x in a.skip.split(",") if x)
    cmd = [PY, "compare.py"]
    for ag in a.agent:
        cmd += ["--agent", ag]
    cmd += ["--baselines", *[b for b in BASELINES if b not in skip]]
    for name, path in (FIELD if a.panel == "field" else OPPONENTS).items():
        if name not in skip:
            cmd += ["--opponent", f"{name}={path}"]
    cmd += ["--seeds-file", sf, "--workers", str(a.workers), "--out", os.path.abspath(a.out)]
    r = subprocess.run(cmd, cwd=SOL, capture_output=True, text=True)
    if r.returncode:
        print((r.stdout + r.stderr)[-3000:]); sys.exit(1)
    s = json.load(open(os.path.join(a.out, "summary.json")))
    for cand, res in s["candidates"].items():
        rows = []; print(f"== {cand}")
        for opp, m in sorted(res["by_opponent"].items()):
            if "score_rate" not in m:
                print(f"  {opp:10} errors {m.get('errors')}"); continue
            rows.append(m["score_rate"])
            print(f"  {opp:10} W/D/L {m['wins']:3}/{m['draws']}/{m['losses']:3}  score {m['score_rate']:.3f}  margin {m['mean_margin']:+8.0f}  errors {m['errors']}")
        print(f"  PANEL MEAN score {sum(rows) / len(rows):.3f} over {len(rows)} opponents")
        bc = res["by_opponent"].get("bc_m15s0", {}).get("score_rate")
        clones = [m["score_rate"] for o, m in res["by_opponent"].items() if "score_rate" in m and o not in ("bc_m15s0", "fukami")]
        if clones:
            print(f"  clone-field mean {sum(clones) / len(clones):.3f} over {len(clones)}; reactive stand-in (bc_m15s0) {bc}")


if __name__ == "__main__":
    main()
