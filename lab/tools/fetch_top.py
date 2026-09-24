"""Download recent replays of top-N LB teams (read-only Kaggle).
usage: python fetch_top.py --top 30 --per-sub 12 --out /workspace/shared/replays/top
Writes index.jsonl (team, rank, score, sub_id, episode_id, file). Skips existing files."""
import argparse, csv, glob, io, json, os, subprocess, zipfile
K = "/workspace/shared/bin/kaggle"

def run(*a):
    return subprocess.run([K, *a], capture_output=True, text=True, timeout=600).stdout

def jl(txt):
    txt = (txt or "").lstrip()
    if not txt.startswith("["): return []
    return json.JSONDecoder().raw_decode(txt)[0]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--per-sub", type=int, default=12); ap.add_argument("--out", default="/workspace/shared/replays/top")
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    tmp = a.out + "/_lb"; os.makedirs(tmp, exist_ok=True)
    run("competitions", "leaderboard", "-c", "kaggriculture", "-d", "-p", tmp)
    z = sorted(glob.glob(tmp + "/*.zip"))[-1]
    with zipfile.ZipFile(z) as zf:
        name = zf.namelist()[0]; rows = list(csv.DictReader(io.TextIOWrapper(zf.open(name), "utf-8-sig")))
    idx = open(a.out + "/index.jsonl", "a")
    for r in rows[: a.top]:
        subs = jl(run("competitions", "team-submissions", r["TeamId"], "--format", "json"))
        for s in subs:
            eps = jl(run("competitions", "episodes", str(s["id"]), "--format", "json"))
            eps = [e for e in eps if "COMPLETED" in e["state"]][: a.per_sub]
            for e in eps:
                f = f"{a.out}/episode-{e['id']}-replay.json.gz"
                if not os.path.exists(f):
                    run("competitions", "replay", str(e["id"]), "-p", a.out, "-q")
                    raw = f[:-3]
                    if os.path.exists(raw): subprocess.run(["gzip", "-f", raw])
                idx.write(json.dumps({"team": r["TeamName"], "team_id": r["TeamId"], "rank": r["Rank"], "score": r["Score"],
                                      "sub_id": s["id"], "sub_score": s.get("publicScore"), "episode_id": e["id"],
                                      "end": e["endTime"], "file": f}) + "\n"); idx.flush()
            print(r["Rank"], r["TeamName"], s["id"], len(eps), flush=True)

if __name__ == "__main__":
    main()
