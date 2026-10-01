"""T046: merge Pavel's old BC3 dataset and our fresh one into ONE training dataset (per team slot dirs of *.npz).

Inputs may be .zip files or directories (any nesting): every directory that contains *.npz is a slot, slot = dir basename
(e.g. mgoose_cn, decem_cn, ...). Only *.npz members are extracted, straight into <out>/<slot>/ (no double copy of the zip).
Duplicates (same slot + same file name, i.e. same episode) are kept once (first source wins: pass the OLD dataset first).
Optionally applies the B1 boundary-target fix (fix_targets.py) into <out>_b1/.

usage (on the GPU box, from Pavel's lab/pavel/bc3 directory so feat3 imports work):
  python merge_datasets.py --src old_bc3.zip --src bc3_fresh.zip --out /data/bc3_merged [--b1] [--init multi15_s0/best.pt]
Prints per-slot counts and the ready-to-run train3_ft.py commands. NEW_* slots (teams without a slot in the m15 checkpoints,
e.g. DSM) are merged but NOT put into the --data list: adding a slot changes g_dim, so it cannot warm-start from m15."""
import argparse, collections, json, os, shutil, subprocess, sys, zipfile

M15_TEAMS = ['mgoose_cn', 'mgoose2_cn', 'decem_cn', 'mmpq_cn', 'boey_cn', 'fourth_quadrant_cn', 'majkel1337_cn',
             'vadim_vasilenko_cn', 'team_cn', 'third_farm_club_cn', 'smackaveli_cn', 'kaggledew_valley_cn', 'mtmr_s1_cn',
             'densike_cn', 'artem_the_farmer_cn']
HERE = os.path.dirname(os.path.abspath(__file__))


def add_zip(z, out, counts, dup, prefix=""):
    with zipfile.ZipFile(z) as zf:
        for m in zf.infolist():
            if m.is_dir() or not m.filename.endswith(".npz"):
                continue
            slot = os.path.basename(os.path.dirname(m.filename.rstrip("/"))) or "root"
            dst = os.path.join(out, slot, prefix + os.path.basename(m.filename))
            if os.path.exists(os.path.join(out, slot, os.path.basename(m.filename))) or os.path.exists(os.path.join(out, slot, "f_" + os.path.basename(m.filename))):
                dup[slot] += 1; continue
            if os.path.exists(dst):
                dup[slot] += 1; continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with zf.open(m) as s, open(dst + ".tmp", "wb") as d:
                shutil.copyfileobj(s, d)
            os.replace(dst + ".tmp", dst); counts[(z, slot)] += 1


def add_dir(root, out, counts, dup, prefix=""):
    for dp, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith(".npz"):
                continue
            slot = os.path.basename(dp); dst = os.path.join(out, slot, prefix + f)
            if os.path.exists(os.path.join(out, slot, f)) or os.path.exists(os.path.join(out, slot, "f_" + f)):
                dup[slot] += 1; continue
            if os.path.exists(dst):
                dup[slot] += 1; continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                os.link(os.path.join(dp, f), dst)
            except OSError:
                shutil.copy(os.path.join(dp, f), dst)
            counts[(root, slot)] += 1


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--src", action="append", required=True, help="zip or dir; OLD first")
    ap.add_argument("--out", required=True); ap.add_argument("--b1", action="store_true", help="also write <out>_b1 with B1-fixed targets")
    ap.add_argument("--init", default="", help="checkpoint whose cfg['teams'] defines the slot order (default: m15 order)")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--val-frac", type=float, default=0.1)
    ap.add_argument("--fresh-from", type=int, default=1, help="sources from this index on (0-based) are FRESH: their files get prefix f_ (for train3_ft --fresh-frac)")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    teams = M15_TEAMS
    if a.init:
        import torch
        teams = torch.load(a.init, map_location="cpu", weights_only=False)["cfg"]["teams"]
    counts, dup = collections.Counter(), collections.Counter()
    for k, s in enumerate(a.src):
        (add_zip if s.endswith(".zip") else add_dir)(s, a.out, counts, dup, "f_" if k >= a.fresh_from else "")
    slots = sorted(d for d in os.listdir(a.out) if os.path.isdir(os.path.join(a.out, d)))
    per = {s: len([f for f in os.listdir(os.path.join(a.out, s)) if f.endswith(".npz")]) for s in slots}
    print("slot counts (after merge):"); [print(f"  {s:28s} {n:5d}") for s, n in per.items()]
    print("per source:"); [print(f"  {os.path.basename(src):40s} {sl:28s} {n}") for (src, sl), n in sorted(counts.items())]
    print("duplicates skipped:", dict(dup))
    unknown = [s for s in slots if s not in teams and not s.startswith("NEW_")]
    if unknown:
        print("WARNING: slots not in the checkpoint team list (ignored by --data):", unknown)
    json.dump(dict(per_slot=per, per_source={f"{k[0]}|{k[1]}": v for k, v in counts.items()}, dup=dup, teams=teams),
              open(os.path.join(a.out, "merge_manifest.json"), "w"), indent=1)
    # fixed validation split shared by all runs: ~val-frac of FRESH episodes (deterministic hash), written once
    import hashlib, re
    fresh_eps = sorted({re.search(r"(\d{6,})", f).group(1) for s in slots for f in os.listdir(os.path.join(a.out, s)) if f.startswith("f_")})
    val = [e for e in fresh_eps if int(hashlib.sha256(f"46000:{e}".encode()).hexdigest(), 16) % 1000 < a.val_frac * 1000]
    open(os.path.join(a.out, "val_ids.txt"), "w").write("\n".join(val) + "\n")
    print(f"val_ids.txt: {len(val)} of {len(fresh_eps)} fresh episodes")
    roots = [a.out]
    if a.b1:
        fx = os.path.join(HERE, "fix_targets.py")
        for s in slots:
            subprocess.run([sys.executable, fx, "--src", os.path.join(a.out, s), "--dst", os.path.join(a.out + "_b1", s),
                            "--workers", str(a.workers)], check=True, env=dict(os.environ, BC3_DIR=os.environ.get("BC3_DIR", HERE)))
        roots.append(a.out + "_b1")
    for r in roots:
        data = ",".join(os.path.join(r, t) for t in teams if per.get(t))
        print(f"\n--data for {r}:\n{data}")


if __name__ == "__main__":
    main()
