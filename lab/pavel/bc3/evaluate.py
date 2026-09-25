"""Standard evaluation of a BC v3 run: agents per decoding variant, handover on held-out worlds, compare.py vs Horizon.
usage: python evaluate.py --run ../../../../bc3_runs/boey_r2 --replays ../../../../replays/56521745 --team Boey \
           --variants greedy,persist --ks 0,240 --seeds 16 --workers 24
Variants: greedy | persist | dedupe | sample | persist+sample ... ('+'-joined flags)."""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))  # ~/personal/kaggle/kaggriculture
PY = os.path.join(ROOT, ".venv", "bin", "python")
SOL = os.path.join(ROOT, "solution")


def sh(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "pyspiel" not in l)
    if r.returncode:
        print(out[-3000:]); raise SystemExit(f"failed: {' '.join(cmd)}")
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--run", required=True); ap.add_argument("--replays", required=True)
    ap.add_argument("--team", required=True); ap.add_argument("--variants", default="greedy,persist"); ap.add_argument("--ks", default="0,240")
    ap.add_argument("--seeds", type=int, default=16); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--ckpt", default="best.pt")
    ap.add_argument("--opponents", default="v5_market", help="compare.py baselines, plus es2c1 for the adil candidate")
    ap.add_argument("--skip-handover", action="store_true"); ap.add_argument("--skip-compare", action="store_true")
    a = ap.parse_args()
    run = os.path.abspath(a.run); name = os.path.basename(run); ckpt = os.path.join(run, a.ckpt)
    split = json.load(open(os.path.join(run, "split.json")))
    val_dir = os.path.join(ROOT, "runs", "val", name); os.makedirs(val_dir, exist_ok=True)
    for f in split["val_files"]:
        src = os.path.join(os.path.abspath(a.replays), f.replace(".npz", "-replay.json.gz")); dst = os.path.join(val_dir, os.path.basename(src))
        if not os.path.exists(dst):
            os.symlink(src, dst)
    agents = {}
    for v in a.variants.split(","):
        flags = v.split("+"); out = os.path.join(ROOT, "runs", "agents", f"{name}_{v.replace('+', '_')}")
        cmd = [PY, os.path.join(HERE, "agent3.py"), "--ckpt", ckpt, "--out", out]
        cmd += ["--persist"] * ("persist" in flags) + ["--dedupe"] * ("dedupe" in flags) + ["--sample"] * ("sample" in flags) + ["--msample"] * ("msample" in flags) + ["--fill"] * ("fill" in flags) + ["--smask"] * ("smask" in flags) + ["--notrip"] * ("notrip" in flags)
        sh(cmd); agents[v] = os.path.join(out, "main.py")
    summary = {}
    if not a.skip_handover:
        for v in a.variants.split(","):
            flags = v.split("+"); opts = ",".join(f for f in flags if f in ("persist", "dedupe", "msample", "fill", "smask", "notrip"))
            cmd = [PY, os.path.join(HERE, "..", "handover.py"), "--ckpt", ckpt, "--glob", os.path.join(val_dir, "*.gz"), "--team", a.team,
                   "--ks", a.ks, "--out", os.path.join(ROOT, "runs", "handover", f"{name}_{v.replace('+', '_')}.jsonl"), "--workers", str(a.workers)]
            if opts:
                cmd += ["--opts", opts]
            if "sample" in flags:
                cmd += ["--sample"]
            print(f"== handover {name} {v}\n" + sh(cmd), flush=True)
    if not a.skip_compare:
        dev = json.load(open(os.path.join(SOL, "seeds", "development.json")))
        seeds_file = os.path.join(ROOT, "runs", "compare", f"dev{a.seeds}.json")
        os.makedirs(os.path.dirname(seeds_file), exist_ok=True)
        json.dump(dict(dev, seeds=dev["seeds"][: a.seeds], purpose=f"development first {a.seeds}"), open(seeds_file, "w"))
        out = os.path.join(ROOT, "runs", "compare", f"{name}_s{a.seeds}")
        n = 1
        while os.path.exists(out):
            n += 1; out = os.path.join(ROOT, "runs", "compare", f"{name}_s{a.seeds}_{n}")
        cmd = [PY, "compare.py"]
        for v, p in agents.items():
            cmd += ["--agent", f"{name}_{v.replace('+', '_')}={p}"]
        base = [o for o in a.opponents.split(",") if o != "es2c1"]
        cmd += ["--baselines", *base] if base else []
        if "es2c1" in a.opponents.split(","):
            cmd += ["--opponent", f"es2c1={os.path.join(ROOT, 'adil-board', 'candidates', 'es2_c1', 'pkg', 'main.py')}"]
        cmd += ["--seeds-file", seeds_file, "--workers", str(a.workers), "--out", out]
        sh(cmd, cwd=SOL)
        s = json.load(open(os.path.join(out, "summary.json")))
        print("== compare", out)
        for cand, r in s["candidates"].items():
            for opp, m in r["by_opponent"].items():
                print(f"  {cand:28} vs {opp:10} W/D/L {m.get('wins')}/{m.get('draws')}/{m.get('losses')}  score {m.get('score_rate', float('nan')):.3f}  "
                      f"margin {m.get('mean_margin', float('nan')):+.0f}  errors {m.get('errors')}")


if __name__ == "__main__":
    main()
