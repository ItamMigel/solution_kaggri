"""Prepare BC v3 data for top-team submissions: canonical market tapes + NOOP-free dataset + determinism check.
usage: python prep_team.py --map ../../../../replays/more_teams.json --workers 24
more_teams.json: {team_id: [team name, submission id, score]} (written when the subs were picked)."""
import argparse, glob, gzip, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
PY = os.path.join(ROOT, ".venv", "bin", "python")


def short(name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s[:20] or "team"


def deterministic(sub, team):
    """Self-play (seed 0) validation episode: identical actions whenever both seats see identical states?"""
    for f in sorted(glob.glob(f"{ROOT}/replays/{sub}/*.gz")):
        d = json.load(gzip.open(f, "rt")); names = d["info"]["TeamNames"]
        if names[0] != names[1]:
            continue
        sym = same = 0
        for t in range(0, 40):
            o0 = d["steps"][t][0]["observation"]; o1 = d["steps"][t][1]["observation"]; fm = o0["farms"]
            if json.dumps(fm[0], sort_keys=True) == json.dumps(fm[1], sort_keys=True) and \
                    json.dumps(o0["private"], sort_keys=True) == json.dumps(o1["private"], sort_keys=True):
                sym += 1
                same += json.dumps(d["steps"][t + 1][0]["action"], sort_keys=True) == json.dumps(d["steps"][t + 1][1]["action"], sort_keys=True)
        return f"{same}/{sym}"
    return "no self-play"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--map", required=True); ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    for tid, (name, sub, score) in json.load(open(a.map)).items():
        sub = str(sub); nm = short(name); n = len(glob.glob(f"{ROOT}/replays/{sub}/*.gz"))
        if n == 0:
            print(name, sub, "no replays yet"); continue
        subprocess.run([PY, os.path.join(HERE, "..", "canon_market.py"), "--glob", f"{ROOT}/replays/{sub}/*.gz",
                        "--out", f"{ROOT}/canon/{sub}", "--workers", str(a.workers)], env=env, capture_output=True)
        r = subprocess.run([PY, os.path.join(HERE, "build3.py"), "--team", name, "--glob", f"{ROOT}/replays/{sub}/*.gz",
                            "--canon", f"{ROOT}/canon/{sub}", "--nonoop", "--out", f"{ROOT}/bc3_data/{nm}_cn", "--workers", str(a.workers)],
                           env=env, capture_output=True, text=True)
        built = len(glob.glob(f"{ROOT}/bc3_data/{nm}_cn/*.npz"))
        print(f"{name:28} sub {sub} score {score} replays {n} built {built} deterministic {deterministic(sub, name)} -> bc3_data/{nm}_cn",
              flush=True)
        if built == 0:
            print((r.stdout + r.stderr)[-800:])


if __name__ == "__main__":
    main()
