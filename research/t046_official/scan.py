import zipfile, json, sys, collections
from concurrent.futures import ProcessPoolExecutor
def scan(args):
    z, name = args
    with zipfile.ZipFile(z) as zf:
        d = json.loads(zf.read(name))
    info = d.get("info", {}); r = d.get("rewards")
    return dict(zip=z[-14:-4], ep=name, teams=info.get("TeamNames"), rewards=r)
if __name__ == "__main__":
    jobs = []
    for z in ["kaggriculture-episodes-2026-09-27.zip", "kaggriculture-episodes-2026-09-28.zip"]:
        jobs += [(z, n) for n in zipfile.ZipFile(z).namelist() if n.endswith(".json")]
    out = open("scan.jsonl", "w"); c = collections.Counter()
    with ProcessPoolExecutor(12) as ex:
        for r in ex.map(scan, jobs, chunksize=4):
            out.write(json.dumps(r) + "\n")
            for t in r["teams"] or []: c[t] += 1
    print(len(jobs), "episodes"); [print(n, t) for t, n in c.most_common(40)]
