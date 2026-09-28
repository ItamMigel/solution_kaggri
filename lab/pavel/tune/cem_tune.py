"""Cross-entropy (CEM) search over module-level knobs of a Horizon-lineage agent (numpy only, no pycma).
Each candidate = base main.py + `globals().update(knobs)` + an agent re-bind (keeps the agent as the last callable).
Fitness = weighted score rate (win 1, draw .5) over a fixed opponent panel on common fresh worlds (both seats),
tie-broken by mean margin. The centre is evaluated every generation on the same worlds for reference.

usage: python cem_tune.py --base .../tetsu1009/main.py --out ../../../../runs/cem_tetsu --gens 10 --pop 16 --worlds 4 --workers 80
"""
import argparse, json, os, subprocess, sys, time
import numpy as np
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PY = os.path.join(ROOT, ".venv", "bin", "python"); WORKER = os.path.join(ROOT, "solution", "game_worker.py")
POOL = os.path.join(ROOT, "adil-board", "opponents", "pool"); CAND = os.path.join(ROOT, "adil-board", "candidates")
PUB = os.path.join(ROOT, "research", "public", "agents")

# name: (lo, hi, kind)  — ranges from lab/tools/knobs.py SPACE plus two shiiin9 market constants
SPACE = {
    "_V92_P_H": (12, 96, "int"), "_V92_P_K": (1, 8, "int"), "_V92_Q_H": (12, 96, "int"),
    "_V92_Q_PF": (0.3, 2.0, "float"), "_V92_Q_PM": (0.0, 1.5, "float"),
    "_CA_MARGIN": (-40.0, 30.0, "float"), "_CA_BUFFER": (0, 30, "int"), "_CA_CASH": (0, 3000, "int"),
    "_OR2_CAP": (5, 80, "int"), "_OR2_SLOT_MARGIN": (0.0, 60.0, "float"), "_CH_SHED": (50, 100, "int"),
    "_SR_MARGIN": (0, 30, "int"), "_HD2_RATIO": (0.8, 2.5, "float"), "_HD2_MIN_GAIN": (0.0, 3000.0, "float"),
    "_HD2_CARE": (0.3, 1.2, "float"), "_CS_RATIO": (0.8, 2.5, "float"), "_CS_MIN_GAIN": (0.0, 3000.0, "float"),
    "_RACE_HORIZON_CLONE": (3, 24, "int"), "_RACE_HORIZON_ESCALATED": (8, 48, "int"), "_Y_MARGIN": (-40, 30, "int"),
    "V9_RACE_DEFAULT": (24, 64, "int"), "_V92_P_EVERY": (1, 4, "int"),
}
KEYS = list(SPACE)

PANEL = [  # (name, path, weight)
    ("mirror", None, 2), ("es7", f"{CAND}/es7_wm/pkg/main.py", 2), ("es3", f"{CAND}/es3_g5/pkg/main.py", 1),
    ("v5_market", f"{ROOT}/solution/agents/horizon_v5_market.py", 1), ("metav4", f"{POOL}/tschinkel_metav4_v13/main.py", 1),
    ("parthenos", f"{POOL}/parthenos_robust/main.py", 1), ("harvest", f"{PUB}/haodou092__kaggriculture-harvest-ledger/main.py", 1),
    ("ozer55", f"{PUB}/ahmedberatozer__kaggriculture-v55-one-turn-market-race-edge/main.py", 1),
    ("bc_m15s0", f"{ROOT}/runs/agents/np_m15s0_mg/main.py", 1),
]


def to_unit(p):
    return np.array([(p[k] - SPACE[k][0]) / (SPACE[k][1] - SPACE[k][0]) for k in KEYS])


def from_unit(u):
    out = {}
    for k, x in zip(KEYS, np.clip(u, 0, 1)):
        lo, hi, kind = SPACE[k]; v = lo + x * (hi - lo)
        out[k] = int(round(v)) if kind == "int" else float(v)
    return out


def write_agent(base_src, knobs, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    src = base_src.rstrip() + "\n\n# --- knob override (lab/pavel/tune/cem_tune.py) ---\nglobals().update(" + json.dumps(knobs) + ")\n"
    src += "_KNOB_AGENT = agent\ndef agent(observation, configuration=None):\n    return _KNOB_AGENT(observation, configuration)\n"
    open(path, "w").write(src)


def play(job):
    cand, opp, seed, seat = job
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    js = json.dumps({"candidate": "c", "opponent": "o", "seed": seed, "seat": seat, "candidate_path": cand, "opponent_path": opp})
    for attempt in range(2):
        try:
            r = subprocess.run([PY, WORKER], input=js, text=True, capture_output=True, timeout=600, cwd=os.path.dirname(cand), env=env)
            res = json.loads(r.stdout.strip().splitlines()[-1])
            if "points" in res:
                return res["points"], res["margin"]
        except Exception:
            pass
    return None, None


def evaluate(paths, panel, seeds, workers):
    jobs = [(i, name, w, (paths[i], opp, s, seat)) for i in range(len(paths)) for name, opp, w in panel for s in seeds for seat in (0, 1)]
    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(play, [j[3] for j in jobs]))
    fit = []; detail = []
    for i in range(len(paths)):
        num = den = mar = 0.0; per = {}; errs = 0
        for (ci, name, w, _), (pt, mg) in zip(jobs, res):
            if ci != i:
                continue
            if pt is None:
                errs += 1; continue
            num += w * pt; den += w; mar += w * mg
            per.setdefault(name, []).append(pt)
        fit.append(num / den + (mar / den) / 1e6 if den else -1.0)
        detail.append({"score": num / den if den else None, "margin": mar / den if den else None, "errors": errs,
                       "per_opp": {k: sum(v) / len(v) for k, v in per.items()}})
    return fit, detail


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--base", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--init", default="", help="json of initial knob values (default: base file's own values)")
    ap.add_argument("--gens", type=int, default=10); ap.add_argument("--pop", type=int, default=16); ap.add_argument("--elite", type=int, default=5)
    ap.add_argument("--sigma", type=float, default=0.08); ap.add_argument("--worlds", type=int, default=4); ap.add_argument("--workers", type=int, default=80)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    base_src = open(a.base).read()
    ns = {"__name__": "base"}; exec(compile(base_src, a.base, "exec"), ns)
    init = {k: ns[k] for k in KEYS if k in ns}
    missing = [k for k in KEYS if k not in ns]
    if missing:
        raise SystemExit(f"base lacks knobs {missing}")
    if a.init:
        init.update(json.load(open(a.init)))
    panel = [(n, (a.base if p is None else p), w) for n, p, w in PANEL]
    rng = np.random.default_rng(a.seed); m = to_unit(init); s = np.full(len(KEYS), a.sigma)
    hist = open(os.path.join(a.out, "history.jsonl"), "a")
    for g in range(a.gens):
        t0 = time.time(); seeds = [int(x) for x in rng.integers(1, 2 ** 31 - 1, a.worlds)]
        us = [m] + [m + s * rng.standard_normal(len(KEYS)) for _ in range(a.pop)]
        us = [np.clip(u, 0, 1) for u in us]
        gdir = os.path.join(a.out, f"gen_{g:03d}"); paths = []
        for i, u in enumerate(us):
            p = os.path.join(gdir, f"c{i:02d}", "main.py"); write_agent(base_src, from_unit(u), p); paths.append(p)
        fit, det = evaluate(paths, panel, seeds, a.workers)
        order = np.argsort(fit[1:])[::-1] + 1
        elite = order[: a.elite]; wts = np.log(a.elite + 0.5) - np.log(np.arange(1, a.elite + 1)); wts /= wts.sum()
        new_m = sum(w * us[i] for w, i in zip(wts, elite))
        s = np.maximum(0.6 * s + 0.4 * np.sqrt(sum(w * (us[i] - m) ** 2 for w, i in zip(wts, elite))), 0.015)
        rec = {"gen": g, "secs": round(time.time() - t0), "seeds": seeds, "centre_fit": fit[0], "centre": det[0],
               "best_fit": fit[order[0]], "best": det[order[0]], "best_knobs": from_unit(us[order[0]]),
               "mean_fit": float(np.mean(fit[1:])), "new_centre_knobs": from_unit(new_m), "sigma_mean": float(s.mean())}
        hist.write(json.dumps(rec) + "\n"); hist.flush()
        print(f"gen {g} {rec['secs']}s centre {fit[0]:.3f} best {fit[order[0]]:.3f} mean {rec['mean_fit']:.3f} sigma {s.mean():.3f} "
              f"centre per-opp {json.dumps({k: round(v, 2) for k, v in det[0]['per_opp'].items()})}", flush=True)
        m = new_m
        json.dump(from_unit(m), open(os.path.join(a.out, "centre.json"), "w"), indent=1)
    print("done; final centre in", os.path.join(a.out, "centre.json"))


if __name__ == "__main__":
    main()
