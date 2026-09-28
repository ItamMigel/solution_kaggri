"""Convert downloaded Kaggle replays (any teams) into generator-format shards (declog rows for BOTH players) so they can be
mixed into build_dataset.py.  usage: python replays_to_shards.py '/path/replays/top50/*/*.gz' runs/shards_top50/shard_top50.jsonl.gz"""
import glob, gzip, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import rows_for
fs = sorted(glob.glob(sys.argv[1])); out = sys.argv[2]; os.makedirs(os.path.dirname(out), exist_ok=True); n = 0
with gzip.open(out, "wt") as w:
    for f in fs:
        try:
            d = json.load(gzip.open(f, "rt")) if f.endswith(".gz") else json.load(open(f))
            names = d["info"]["TeamNames"]; rew = d["rewards"]
            if None in rew or len(names) != 2: continue
            gid = "kaggle_" + str(d["info"].get("EpisodeId", os.path.basename(f)))
            for p in (0, 1):
                for r in rows_for(d["steps"], p, names, rew, gid, d["info"].get("seed")): w.write(json.dumps(r, separators=(",", ":")) + "\n")
            n += 1
        except Exception as e:
            print("skip", f, repr(e)[:120])
print("converted episodes", n)
