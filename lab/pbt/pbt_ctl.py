#!/usr/bin/env python3
"""PBT controller = evolution over PPO agents.

Every member (runs/pbt/mI, one per GPU) trains PPO in rounds of K iterations (scripts/pbt_member.sh).
This controller, on CPU:
  1. evaluates the newest round checkpoint of every member in the OFFICIAL engine
     (one compare.py call, common worlds for all members) vs es3_g5 / es1_g9 / v5_market;
  2. fitness = mean score rate + mean margin / 40000, smoothed over the member's last 2 evals;
  3. exploit/explore: the worst member copies the best member's evaluated weights and gets
     perturbed hyper-parameters (written as mI/EXPLOIT.json, applied by the member between rounds);
  4. hall of fame: best evaluated checkpoint -> runs/pbt/best/ (+ Kaggle tar for the HUMAN; agents never submit).
"""
import argparse, glob, json, os, random, re, shutil, subprocess, sys, tarfile, time

HP_BOUNDS = {"lr": (1e-6, 4e-5), "ent": (1e-4, 1e-2), "clip": (.06, .25), "kl_floor": (0.0, .05), "target_kl": (.005, .05)}


def perturb(hp, rng):
    hp = dict(hp)
    for k, (lo, hi) in HP_BOUNDS.items():
        if k == "kl_floor":
            v = hp[k] * rng.choice([.5, 1.5]) if hp[k] > 0 else rng.choice([0.0, 0.0, .005])
        else:
            v = hp[k] * rng.choice([.7, .8, 1.25, 1.4])
        hp[k] = float(min(hi, max(lo, v)))
    # "teachers" genes: the style the member plays as, and which frozen team doubles it trains against
    teams = os.environ.get("PBT_TEAMS", "").split()
    if teams and rng.random() < .15:
        hp["team"] = rng.choice(teams)
    pool = os.environ.get("PBT_OPPS", "").split()
    if pool and rng.random() < .3:
        cur = [t for t in hp.get("opps", pool) if t != "*"] if hp.get("opps") != ["*"] else list(pool)
        t = rng.choice(pool)
        cur = [x for x in cur if x != t] if t in cur else cur + [t]
        hp["opps"] = cur or [rng.choice(pool)]
    if rng.random() < .2:
        hp["epochs"] = 3 - hp["epochs"] if hp["epochs"] in (1, 2) else 1
    return hp


def newest_ckpt(mdir):
    """Return the last *published PBT round* checkpoint.

    `itNNN.pt` is PPO's training-age namespace.  An exploit can intentionally
    jump a member back to an older donor age, so it is not monotonic per member
    and cannot safely identify a PBT generation.  Members publish roundNNN.pt
    only after a successful round.  Keep the `it` fallback for an interrupted
    old run, so its status can still be inspected/recovered.
    """
    cks = glob.glob(f"{mdir}/round*.pt") or glob.glob(f"{mdir}/it*.pt")
    cks = sorted(cks, key=lambda p: int(re.search(r"(?:round|it)(\d+)\.pt$", p).group(1)))
    return cks[-1] if cks else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)          # runs/pbt
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--py", default=sys.executable)
    ap.add_argument("--members", type=int, default=4)
    ap.add_argument("--team", default="dsm")
    ap.add_argument("--worlds", type=int, default=6)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--margin-delta", type=float, default=.03, help="exploit only if best-worst fitness gap exceeds this")
    ap.add_argument("--start", default="", help="also evaluate this checkpoint once as the reference")
    ap.add_argument("--poll", type=int, default=60)
    a = ap.parse_args()
    rng = random.Random(12345)
    lab, harness = f"{a.pkg}/code/lab", f"{a.pkg}/code/harness"
    fit_path = f"{a.root}/fitness.jsonl"
    done = set()
    hist = {}  # member -> list of fitness
    if os.path.exists(fit_path):
        for line in open(fit_path):
            r = json.loads(line)
            done.add(r["ckpt"])
            if r["member"].startswith("m"):
                hist.setdefault(r["member"], []).append(r["fitness"])
    seed_pool = json.load(open(f"{harness}/seeds/v5_development.json"))["seeds"]
    if not 0 < a.worlds <= len(seed_pool):
        ap.error(f"worlds must be in [1, {len(seed_pool)}]")
    gen = len(glob.glob(f"{a.root}/eval/gen_*"))
    while True:
        todo = {}
        for i in range(a.members):
            ck = newest_ckpt(f"{a.root}/m{i}")
            if ck and ck not in done and not os.path.exists(f"{a.root}/m{i}/EXPLOIT.json"):
                todo[f"m{i}"] = ck
        if a.start:
            # The start checkpoint is a CONTROL in every generation: worlds rotate and their difficulty varies a lot
            # (opponents score 94k on one world, 162k on another), so fitness is measured relative to the control.
            todo["start"] = a.start
        fresh = [m for m in todo if m != "start"]
        # A PBT generation must contain all members.  Comparing a new result to
        # an old result from a different seed fold makes exploit decisions
        # meaningless, and a two-member exam silently leaves half the
        # population out of selection.
        if len(fresh) < a.members:
            time.sleep(a.poll); continue
        # Rotate deterministic, common folds.  This prevents evolution from
        # repeatedly fitting just the first six development worlds while
        # preserving an exactly paired exam within each generation.
        offset = (gen * a.worlds) % len(seed_pool)
        seeds = [seed_pool[(offset + j) % len(seed_pool)] for j in range(a.worlds)]
        gdir = f"{a.root}/eval/gen_{gen:03d}"; os.makedirs(gdir, exist_ok=True)
        # snapshot the evaluated weights (members keep training and may overwrite their files)
        agents, pool = [], {}
        for m, ck in todo.items():
            # `roundNNN` is unique even when exploit restores an older PPO
            # iteration.  It also makes the donor pool immutable: never reuse
            # a pool/m0.pt path that a later evaluation could overwrite before
            # the recipient consumes EXPLOIT.json.
            suffix = os.path.basename(ck).removesuffix(".pt")
            tag = f"{m}_{suffix}"
            snap = f"{a.root}/pool/{tag}.pt"; os.makedirs(os.path.dirname(snap), exist_ok=True); shutil.copy(ck, snap)
            os.makedirs(f"{gdir}/{tag}", exist_ok=True)
            side = ck[:-3] + ".team"
            team = open(side).read().strip() if os.path.exists(side) else a.team
            subprocess.run([a.py, f"{lab}/bc/export.py", "--ckpt", snap, "--team", team, "--out", f"{gdir}/{tag}/main.py", "--sample"], check=True)
            agents += ["--agent", f"{tag}={gdir}/{tag}/main.py"]; pool[m] = (tag, snap, ck)
        cmd = [a.py, "compare.py", *agents, "--baselines", "v5_market",
               "--opponent", "es3_g5=candidates/es3_g5/main.py", "--opponent", "es1_g9=candidates/es1_g9/main.py",
               "--seeds", *map(str, seeds), "--workers", str(a.workers), "--game-timeout", str(a.timeout), "--out", f"{gdir}/arena"]
        t0 = time.time()
        # compare.py uses one process per worker.  PBT members retain OMP=4 for
        # GPU work; inheriting that into 24 official-engine workers otherwise
        # creates about 96 BLAS/OpenMP threads and starves all four GPUs.
        eval_env = os.environ.copy()
        eval_env.update(OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
        with open(f"{gdir}/compare.log", "w") as compare_log:
            subprocess.run(cmd, cwd=harness, check=False, stdout=compare_log,
                           stderr=subprocess.STDOUT, env=eval_env)
        try:
            summ = json.load(open(f"{gdir}/arena/summary.json"))
            if not summ.get("evaluation_valid", False):
                raise RuntimeError("official-engine evaluation is invalid")
        except Exception as exc:
            print(f"gen {gen}: compare failed ({exc}), see {gdir}/compare.log", flush=True); gen += 1; time.sleep(a.poll); continue
        results = {}
        def raw_fit(tag):
            byo = summ["candidates"].get(tag, {}).get("by_opponent", {})
            rates = [v["score_rate"] for v in byo.values() if "score_rate" in v]
            margins = [v["mean_margin"] for v in byo.values() if "mean_margin" in v]
            return sum(rates) / len(rates) + sum(margins) / len(margins) / 40000 if rates else None
        control = raw_fit(pool["start"][0]) if "start" in pool else None
        for m, (tag, snap, ck) in pool.items():
            byo = summ["candidates"].get(tag, {}).get("by_opponent", {})
            rates = [v["score_rate"] for v in byo.values() if "score_rate" in v]
            margins = [v["mean_margin"] for v in byo.values() if "mean_margin" in v]
            if not rates:
                continue
            raw = sum(rates) / len(rates) + sum(margins) / len(margins) / 40000
            fit = raw - control if control is not None else raw  # relative to the control on the SAME worlds
            row = {"gen": gen, "member": m, "tag": tag, "ckpt": ck, "snap": snap, "seeds": seeds,
                   "fitness": fit, "fitness_raw": raw, "control_raw": control, "secs": round(time.time() - t0),
                   "by_opp": {o: {"wdl": [v.get("wins"), v.get("draws"), v.get("losses")], "rate": v.get("score_rate"),
                                  "margin": v.get("mean_margin"), "errors": v.get("errors")} for o, v in byo.items()}}
            results[m] = row
            if m == "start":
                print(f"gen {gen} control {tag}: raw {raw:.3f} " + " ".join(
                    f"{o}:{r['wdl'][0]}/{r['wdl'][1]}/{r['wdl'][2]} {r['margin']:+.0f}" for o, r in row["by_opp"].items()), flush=True)
                with open(fit_path, "a") as fh:
                    fh.write(json.dumps(row) + "\n")
                continue
            done.add(ck)
            if m.startswith("m"):
                hist.setdefault(m, []).append(fit)
                # This is the PBT selection statistic.  Keep raw `fitness`
                # too, so an analysis can distinguish a lucky one-fold exam
                # from the two-fold value that actually drove exploitation.
                row["fitness_smoothed"] = sum(hist[m][-2:]) / len(hist[m][-2:])
            with open(fit_path, "a") as fh:
                fh.write(json.dumps(row) + "\n")
            best_path = f"{a.root}/best/best.json"
            best = json.load(open(best_path)) if os.path.exists(best_path) else {"fitness": -1e9}
            hall_fit = row.get("fitness_smoothed", fit)
            if hall_fit > best.get("fitness_smoothed", best["fitness"]):
                os.makedirs(f"{a.root}/best", exist_ok=True)
                shutil.copy(snap, f"{a.root}/best/best.pt"); shutil.copy(f"{gdir}/{tag}/main.py", f"{a.root}/best/main.py")
                with tarfile.open(f"{a.root}/best/submission_pbt_best.tar.gz", "w:gz") as t: t.add(f"{gdir}/{tag}/main.py", arcname="main.py")
                json.dump(row, open(best_path, "w"), indent=1)
            print(f"gen {gen} {tag}: fitness vs control {fit:+.3f} (raw {raw:.3f}) " + " ".join(
                f"{o}:{r['wdl'][0]}/{r['wdl'][1]}/{r['wdl'][2]} {r['margin']:+.0f}" for o, r in row["by_opp"].items()), flush=True)
        # exploit / explore among members with at least one eval
        smooth = {m: sum(h[-2:]) / len(h[-2:]) for m, h in hist.items() if h}
        if len(smooth) >= 2:
            order = sorted(smooth, key=smooth.get)
            worst, best_m = order[0], order[-1]
            donor = results.get(best_m) or next((json.loads(l) for l in reversed(open(fit_path).readlines())
                                                 if json.loads(l)["member"] == best_m), None)
            if donor and smooth[best_m] - smooth[worst] > a.margin_delta:
                hp = json.load(open(f"{a.root}/{best_m}/hp.json"))
                new = perturb(hp, rng)
                exploit_path = f"{a.root}/{worst}/EXPLOIT.json"
                tmp_path = exploit_path + ".tmp"
                with open(tmp_path, "w") as fh:
                    json.dump({"donor": best_m, "ckpt": donor["snap"], "hp": new, "gen": gen}, fh, indent=1)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp_path, exploit_path)
                hist[worst] = []  # fresh start for the replaced member
                print(f"gen {gen}: EXPLOIT {worst} ({smooth[worst]:.3f}) <- {best_m} ({smooth[best_m]:.3f}) {donor['tag']}; new hp {new}", flush=True)
        gen += 1


if __name__ == "__main__":
    main()
