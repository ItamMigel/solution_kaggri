"""T046: build a fresh BC3 dataset (Pavel's recipe: canon_market -> build3 --canon --nonoop) from
 (a) official Kaggle top-episode dataset zips (kaggle/kaggriculture-episodes-YYYY-MM-DD) and
 (b) crawled replays (research/t045_fresh/replays/<sub>/*.gz).
Every seat whose team maps to a slot below is built into <out>/<slot>/episode-<id>.npz; each episode is processed once.
Writes <out>/manifest.jsonl (slot, team, episode, source, date, won, margin, canon_verified).
usage: python build_fresh.py --zips a.zip,b.zip --replays DIR --out DIR --workers 16"""
import argparse, glob, gzip, json, os, shutil, subprocess, sys, tempfile, zipfile
from concurrent.futures import ProcessPoolExecutor

_H = os.path.dirname(os.path.abspath(__file__))
# Pavel's lab/pavel dir (contains canon_market.py and bc3/build3.py); default: this file lives in lab/pavel/bc3 of the kit
P = os.environ.get("PAVEL_DIR", os.path.dirname(_H) if os.path.exists(os.path.join(os.path.dirname(_H), "canon_market.py")) else "/workspace/shared/pavel_lab/lab/pavel")
PY = os.environ.get("PY", sys.executable)
ENV = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
# existing m15 slots (names must match cfg['teams'] of the m15 checkpoints) + candidate NEW slots (kept in separate dirs)
SLOT = {"Unknown Mother-Goose": "mgoose_cn", "DECEM": "decem_cn", "M & M & P & Q": "mmpq_cn", "Boey": "boey_cn",
        "Fourth Quadrant": "fourth_quadrant_cn", "Majkel1337": "majkel1337_cn", "Vadim Vasilenko": "vadim_vasilenko_cn",
        "THIRD FARM CLUB": "third_farm_club_cn", "Smackaveli": "smackaveli_cn", "Kaggledew Valley 🏆": "kaggledew_valley_cn",
        "mtmr_s1": "mtmr_s1_cn", "Densike": "densike_cn", "Artem The Farmer 🍅": "artem_the_farmer_cn",
        # new (no slot in m15 yet)
        "DSM": "NEW_dsm_cn", "Azat Akhtyamov": "NEW_azat_akhtyamov_cn", "Victor @ Tufa Labs": "NEW_victor_tufa_cn",
        "Anton Tikhonov": "NEW_anton_tikhonov_cn", "Yizhou": "NEW_yizhou_cn"}


def one(job):
    src, key, date, out = job
    tmp = tempfile.mkdtemp(prefix="t046_", dir=os.environ.get("T046_TMP") or None)
    try:
        ep = key
        f = os.path.join(tmp, f"episode-{ep}-replay.json.gz")
        if src.endswith(".zip"):
            with zipfile.ZipFile(src) as zf, zf.open(f"{ep}.json") as s, gzip.open(f, "wb", 3) as d:
                shutil.copyfileobj(s, d)
        else:
            shutil.copy(src, f)
        with gzip.open(f, "rt") as fh:
            d = json.load(fh)
        names = d["info"].get("TeamNames") or []; rew = d.get("rewards") or [None, None]; del d
        todo = [(i, n) for i, n in enumerate(names) if n in SLOT]
        if not todo or len(set(names)) < 2:
            return []
        subprocess.run([PY, f"{P}/canon_market.py", "--glob", f, "--out", f"{tmp}/canon", "--workers", "1"], env=ENV, capture_output=True)
        cf = f"{tmp}/canon/episode-{ep}.json"
        ver = json.load(open(cf)).get("verified") if os.path.exists(cf) else None
        if not ver:
            return [dict(episode=ep, source=src, status="canon_fail", verified=ver)]
        recs = []
        for i, n in todo:
            slot = SLOT[n]; od = f"{tmp}/npz_{slot}"
            r = subprocess.run([PY, f"{P}/bc3/build3.py", "--team", n, "--glob", f, "--canon", f"{tmp}/canon", "--nonoop", "--out", od,
                                "--workers", "1"], env=ENV, capture_output=True, text=True)
            src_npz = f"{od}/episode-{ep}.npz"
            if not os.path.exists(src_npz):
                recs.append(dict(episode=ep, team=n, status="build_fail", err=(r.stdout + r.stderr)[-300:])); continue
            os.makedirs(f"{out}/{slot}", exist_ok=True); shutil.move(src_npz, f"{out}/{slot}/episode-{ep}.npz")
            won = None if None in rew else bool(rew[i] > rew[1 - i]); margin = None if None in rew else rew[i] - rew[1 - i]
            recs.append(dict(slot=slot, team=n, episode=ep, seat=i, source=os.path.basename(os.path.dirname(src)) if not src.endswith(".zip") else os.path.basename(src),
                             date=date, won=won, margin=margin, opponent=names[1 - i], canon_verified=True, status="ok"))
        return recs
    except Exception as e:
        return [dict(episode=key, source=src, status="error", err=repr(e)[-300:])]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--zips", default=""); ap.add_argument("--replays", default="")
    ap.add_argument("--out", required=True); ap.add_argument("--workers", type=int, default=16); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    jobs, seen = [], set()
    for z in filter(None, a.zips.split(",")):
        date = os.path.basename(z)[-14:-4]
        for n in zipfile.ZipFile(z).namelist():
            if n.endswith(".json"):
                ep = n[:-5]; seen.add(ep); jobs.append((z, ep, date, a.out))
    for f in sorted(glob.glob(f"{a.replays}/*/*.gz")) if a.replays else []:
        ep = os.path.basename(f).split("-")[1]
        if ep not in seen:
            seen.add(ep); jobs.append((f, ep, "crawl", a.out))
    done = set()
    mf = f"{a.out}/manifest.jsonl"
    if os.path.exists(mf):
        done = {str(json.loads(l)["episode"]) for l in open(mf)}
    jobs = [j for j in jobs if j[1] not in done][: a.limit or None]
    print(len(jobs), "episodes to process", flush=True)
    with ProcessPoolExecutor(a.workers) as ex, open(mf, "a") as m:
        for k, recs in enumerate(ex.map(one, jobs), 1):
            for r in recs or [dict(episode=jobs[k - 1][1], status="skip_noteam")]:
                m.write(json.dumps(r, ensure_ascii=False) + "\n")
            m.flush()
            if k % 50 == 0:
                print(k, "/", len(jobs), flush=True)
    print("BUILD_DONE", flush=True)


if __name__ == "__main__":
    main()
