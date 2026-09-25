"""Download all completed episode replays of given Kaggle submissions (read-only Kaggle API).
usage: python fetch_subs.py --subs 56521745,56526629 --out ../../replays --workers 6
Writes <out>/<sub_id>/episode-<id>-replay.json.gz and appends <out>/index.jsonl. Skips existing files.
Needs KAGGLE_API_TOKEN in the environment. Never submits anything."""
import argparse, gzip, json, os, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

KAGGLE = os.path.join(os.path.dirname(sys.executable), "kaggle")


def run(*a, timeout=900):
    return subprocess.run([KAGGLE, "competitions", *a], capture_output=True, text=True, timeout=timeout)


def jl(txt):
    txt = (txt or "").lstrip()
    return json.JSONDecoder().raw_decode(txt)[0] if txt.startswith("[") else []


def fetch(job):
    sub, ep, out = job
    d = os.path.join(out, str(sub)); f = os.path.join(d, f"episode-{ep}-replay.json.gz")
    if os.path.exists(f):
        return sub, ep, "skip"
    raw = os.path.join(d, f"episode-{ep}-replay.json")
    for attempt in range(6):
        r = run("replay", str(ep), "-p", d, "-q")
        if os.path.exists(raw):
            with open(raw, "rb") as src, gzip.open(f + ".tmp", "wb", 6) as dst:
                shutil.copyfileobj(src, dst)
            os.replace(f + ".tmp", f); os.remove(raw)
            return sub, ep, "ok"
        # back off on rate limits (HTTP 429) and other transient errors: 15, 30, 60, 120, 240 s
        time.sleep(15 * 2 ** attempt)
    return sub, ep, f"fail: {(r.stderr or r.stdout)[-200:]!r}"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--subs", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=6); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    jobs = []; meta = {}
    for sub in a.subs.split(","):
        os.makedirs(os.path.join(a.out, sub), exist_ok=True)
        for attempt in range(6):
            r = run("episodes", sub, "--format", "json")
            if (r.stdout or "").lstrip().startswith("["):
                break
            print(sub, "episode listing failed, retrying:", (r.stderr or r.stdout)[-120:], flush=True)
            time.sleep(15 * 2 ** attempt)
        eps = [e for e in jl(r.stdout) if "COMPLETED" in e["state"]]
        if a.limit:
            eps = eps[: a.limit]
        for e in eps:
            jobs.append((sub, e["id"], a.out)); meta[e["id"]] = e
        print(sub, len(eps), "episodes", flush=True)
    with ThreadPoolExecutor(a.workers) as ex, open(os.path.join(a.out, "index.jsonl"), "a") as idx:
        for n, (sub, ep, st) in enumerate(ex.map(fetch, jobs), 1):
            idx.write(json.dumps({"sub_id": sub, "episode_id": ep, "status": st, "end": meta[ep].get("endTime")}) + "\n"); idx.flush()
            if st.startswith("fail") or n % 25 == 0:
                print(n, "/", len(jobs), sub, ep, st, flush=True)
    print("done", len(jobs), flush=True)


if __name__ == "__main__":
    main()
