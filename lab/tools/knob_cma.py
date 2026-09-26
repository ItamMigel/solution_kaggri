"""CMA-ES over Horizon v5 knobs (team suggestion) — same interface/fitness as knob_es.py.
Warm start from a params.json; common fresh worlds per generation; centre evaluated each gen for reference.
usage: python knob_cma.py --init /workspace/shared/candidates_wip/es1_g13/params.json --out /workspace/shared/runs/cma1 --gens 40"""
import argparse, hashlib, json, os, pickle, random, sys, time
import numpy as np, cma
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knobs, knob_es as E

DEFAULT_MIRROR = "/workspace/shared/candidates/es2_c1/pkg/main.py"
FITNESS_MODES = ("uniform", "parthenos_x2")

def panel(mirror):
    return ["--baselines", "v5_market", "--opponent", f"best={mirror}",
            "--opponent", f"yhay0913={E.POOL}/yhay_router0913/main.py",
            "--opponent", f"parthenos={E.POOL}/parthenos_robust/main.py",
            "--opponent", f"metav4={E.POOL}/tschinkel_metav4_v13/main.py"]

def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()

def _atomic_json(path, value):
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(value, f, indent=1)
        f.write("\n")
    os.replace(tmp, path)

def _fitness_weights(mode):
    if mode == "uniform":
        return {"best": 1, "yhay0913": 1, "parthenos": 1, "metav4": 1, "v5_market": 1}
    if mode == "parthenos_x2":
        # The independent gate has repeatedly found the adverse direction here.
        # Keep every opponent in the objective, but make P 2/6 rather than 1/5.
        return {"best": 1, "yhay0913": 1, "parthenos": 2, "metav4": 1, "v5_market": 1}
    raise ValueError(f"unknown fitness mode: {mode}")

def _fitness_from_games(gdir, candidates, mode):
    """Return weighted fitness and durable per-opponent means from compare output.

    This deliberately reuses the exact game score used by knob_es.  We weight
    *means*, not individual rows, so a panel expansion cannot silently change
    an opponent's intended weight.
    """
    rows = {name: {} for name, _ in candidates}
    for line in open(f"{gdir}/run/games.jsonl"):
        d = json.loads(line)
        if d.get("error") or "rewards" not in d:
            continue
        name, opponent = d["candidate"], d["opponent"]
        if name not in rows:
            raise RuntimeError(f"unexpected candidate in compare output: {name}")
        seat = d["seat"]
        margin = d["rewards"][seat] - d["rewards"][1 - seat]
        rows[name].setdefault(opponent, []).append((1.0 if margin > 0 else .5 if margin == 0 else 0.0) + margin / 40000)
    weights = _fitness_weights(mode)
    fit, breakdown = {}, {}
    for name in rows:
        missing = set(weights) - set(rows[name])
        extra = set(rows[name]) - set(weights)
        if missing or extra or any(not rows[name][opp] for opp in weights):
            raise RuntimeError(f"incomplete opponent fitness for {name}: missing={sorted(missing)}, extra={sorted(extra)}")
        means = {opp: float(np.mean(rows[name][opp])) for opp in weights}
        value = sum(weights[opp] * means[opp] for opp in weights) / sum(weights.values())
        fit[name] = float(value)
        breakdown[name] = {"by_opponent": means, "weights": weights, "weighted_fitness": float(value)}
    return fit, breakdown

def _parse_transition(text):
    try:
        start, mode = text.split(":", 1)
        start = int(start)
    except (AttributeError, ValueError):
        raise ValueError("--fitness-transition must be GEN:MODE, e.g. 9:parthenos_x2")
    if start < 1 or mode not in FITNESS_MODES:
        raise ValueError(f"invalid fitness transition {text!r}")
    return start, mode

def _mode_for_generation(schedule, generation):
    phases = [phase for phase in schedule if phase["start_gen"] <= generation]
    if not phases:
        raise RuntimeError(f"fitness schedule has no phase for generation {generation}")
    return phases[-1]["mode"]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--init", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--gens", type=int, default=40); ap.add_argument("--pop", type=int, default=12); ap.add_argument("--sigma", type=float, default=0.06)
    ap.add_argument("--worlds", type=int, default=8); ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--collect", action="store_true", help="append Horizon+ M1 COLLECT module to every candidate (es2_c1 family)")
    ap.add_argument("--fitness", choices=FITNESS_MODES, default="uniform",
                    help="fitness for a new run (existing runs use their recorded schedule)")
    ap.add_argument("--fitness-transition", metavar="GEN:MODE",
                    help="one-time, boundary-only migration of a legacy run; preserves its CMA state")
    ap.add_argument("--mirror", default=os.environ.get("CMA_BEST", DEFAULT_MIRROR),
                    help="frozen control in the fitness panel (default: $CMA_BEST, then legacy es2_c1)")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    a.mirror = os.path.abspath(a.mirror)
    if not os.path.isfile(a.mirror):
        ap.error(f"--mirror does not exist: {a.mirror}")
    E.PANEL = panel(a.mirror)
    base_cfg = {"init": os.path.abspath(a.init), "mirror": a.mirror,
           "mirror_sha256": hashlib.sha256(open(a.mirror, "rb").read()).hexdigest(),
           "collect": a.collect, "pop": a.pop, "sigma0": a.sigma, "worlds": a.worlds}
    cp = f"{a.out}/config.json"
    if os.path.exists(cp):
        old = json.load(open(cp))
        if {k: old.get(k) for k in base_cfg} != base_cfg:
            ap.error(f"existing run config differs: {cp}")
        if "fitness_schedule" not in old:
            if not a.fitness_transition:
                ap.error("legacy run has no fitness schedule; use --fitness-transition GEN:MODE at a completed-generation boundary")
            try:
                start, mode = _parse_transition(a.fitness_transition)
            except ValueError as e:
                ap.error(str(e))
            hp0, sp0 = f"{a.out}/history.json", f"{a.out}/cma.pkl"
            if not (os.path.exists(hp0) and os.path.exists(sp0)):
                ap.error("fitness transition requires existing history.json and cma.pkl")
            hist0 = json.load(open(hp0))
            if len(hist0) != start:
                ap.error(f"fitness transition start {start} must equal completed history length {len(hist0)}")
            transition_path = f"{a.out}/fitness_transition.json"
            if os.path.exists(transition_path):
                ap.error(f"fitness transition already recorded: {transition_path}")
            prior_sha = _sha(cp)
            transition = {"old_config_sha256": prior_sha, "history_sha256": _sha(hp0), "cma_state_sha256": _sha(sp0),
                          "completed_generations": len(hist0), "schedule": [{"start_gen": 0, "mode": "uniform"}, {"start_gen": start, "mode": mode}]}
            _atomic_json(transition_path, transition)
            old = {**old, "fitness_schedule": transition["schedule"]}
            _atomic_json(cp, old)
        elif a.fitness_transition:
            ap.error("run already has an immutable fitness schedule; refusing a second transition")
        schedule = old["fitness_schedule"]
    else:
        if a.fitness_transition:
            ap.error("--fitness-transition is only for an existing legacy run")
        schedule = [{"start_gen": 0, "mode": a.fitness}]
        _atomic_json(cp, {**base_cfg, "fitness_schedule": schedule})
    if not schedule or schedule[0].get("start_gen") != 0:
        ap.error("invalid fitness schedule in config")
    if any(phase.get("mode") not in FITNESS_MODES for phase in schedule) or any(schedule[i]["start_gen"] >= schedule[i + 1]["start_gen"] for i in range(len(schedule) - 1)):
        ap.error("invalid fitness schedule in config")
    if a.collect:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hplus")); import modules as HM
        _orig = knobs.make_agent_file
        def _mk(params, out, base=knobs.BASE):
            ov = _orig(params, out, base); HM.build(out, {"m1_on": True, "m1_ops": ["COLLECT_FERTILIZER"]}, out); return ov
        knobs.make_agent_file = _mk
    sp = f"{a.out}/cma.pkl"; hp = f"{a.out}/history.json"
    if os.path.exists(sp):
        es = pickle.load(open(sp, "rb")); hist = json.load(open(hp))
    else:
        p0 = json.load(open(a.init)); x0 = np.array([(p0[k] - E.LO[i]) / (E.HI[i] - E.LO[i]) for i, k in enumerate(E.NAMES)])
        es = cma.CMAEvolutionStrategy(np.clip(x0, 0, 1), a.sigma, {"popsize": a.pop, "bounds": [0, 1], "seed": 7, "verbose": -9}); hist = []
    confirm = set(json.load(open(f"{E.ROOT}/seeds/v5_confirmation.json"))["seeds"]) | set(json.load(open(f"{E.ROOT}/seeds/confirmation.json"))["seeds"])
    while len(hist) < a.gens:
        g = len(hist); rng = random.Random(90210 + g); seeds = []
        while len(seeds) < a.worlds:
            s = rng.randrange(1, 2**31 - 1)
            if s not in confirm: seeds.append(s)
        X = es.ask(); centre = es.mean.copy()
        cands = [("c", centre)] + [(f"x{i}", np.asarray(x)) for i, x in enumerate(X)]
        gdir = f"{a.out}/gen_{g:03d}"; os.makedirs(gdir, exist_ok=True); t0 = time.time()
        _uniform_fit, err = E.evaluate(cands, seeds, gdir, a.workers)
        mode = _mode_for_generation(schedule, g)
        fit, breakdown = _fitness_from_games(gdir, cands, mode)
        es.tell(X, [-fit[f"x{i}"] for i in range(len(X))])
        best = max(fit, key=fit.get)
        rec = {"gen": g, "seeds": seeds, "fitness_mode": mode, "fit": fit, "fitness_breakdown": breakdown, "errors": err, "centre_fit": fit["c"], "best": best, "best_fit": fit[best],
               "sigma": float(es.sigma), "centre_params": E.to_params(centre), "best_params": E.to_params(dict(cands)[best]),
               "new_mean_params": E.to_params(es.mean), "secs": round(time.time() - t0)}
        hist.append(rec); _atomic_json(hp, hist)
        sp_tmp = f"{sp}.tmp.{os.getpid()}"
        with open(sp_tmp, "wb") as f: pickle.dump(es, f)
        os.replace(sp_tmp, sp)
        print(json.dumps({k: rec[k] for k in ("gen", "centre_fit", "best", "best_fit", "sigma", "errors", "secs")}), flush=True)

if __name__ == "__main__":
    main()
