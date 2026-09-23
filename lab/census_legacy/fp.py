"""Fingerprint extractor: replay (.json.gz) -> compact per-player feature record.

Reuses src.replay_mine.mine (bit-exact engine re-run) and reduces its output to the
feature vector used for the top-7 frontier fingerprint.

Usage:
  python fp.py <replay.json.gz> [...]        -> writes <out_dir>/<episode>.json
  python fp.py --local <agentA.py> <agentB.py> --seed N   -> same features from a local match
"""
import gzip, json, os, sys, glob

sys.path.insert(0, "/workspace/kaggriculture")
OUT = "/workspace/kaggriculture/replays_mine/fp"


def features(r):
    """r = output of replay_mine.mine -> list of 2 feature dicts."""
    out = []
    last = r["tiles_hist"][-1] if r["tiles_hist"] else (0, [{}, {}], {}, {}, [0, 0], [[], []], [])
    for p in range(2):
        tiles = last[1][p]
        sells = {k: v[0] for k, v in r["sells"][p].items()}
        sellrev = {k: round(v[1]) for k, v in r["sells"][p].items()}
        buys = {k: v[0] for k, v in r["buys"][p].items()}
        buycost = {k: round(v[1]) for k, v in r["buys"][p].items()}
        seeds = {k.split(":", 1)[1]: v for k, v in buys.items() if k.startswith("BUY_SEED:")}
        animals = {k.split(":", 1)[1]: v for k, v in buys.items() if k.startswith("BUY_ANIMAL:")}
        prods = {k.split(":", 1)[1]: v for k, v in buys.items() if k.startswith("BUY_PRODUCT:")}
        herd = {a: tiles.get("A_" + a, 0) for a in ("COW", "SHEEP", "GOOSE")}
        crop_tiles = {k[2:]: v for k, v in tiles.items() if k.startswith("P_")}
        out.append({
            "episode": r["episode"], "seed": r["seed"], "name": r["names"][p], "pid": p,
            "money": r["rewards"][p], "opp_money": r["rewards"][1 - p],
            "herd": herd, "n_animals": sum(herd.values()),
            "hands": last[4][p], "quadrants": sorted(last[5][p]), "n_quad": len(last[5][p]),
            "crop_tiles_end": crop_tiles, "n_crop_tiles_end": sum(crop_tiles.values()),
            "seeds": seeds, "n_seeds": sum(seeds.values()),
            "animals_bought": animals, "products_bought": prods,
            "sells": sells, "sell_rev": sellrev,
            "revenue": round(sum(v[1] for v in r["sells"][p].values())),
            "buy_cost": round(sum(v[1] for v in r["buys"][p].values())),
            "hire_cost": round(r["hire_cost"][p]),
            "land": r["land"][p],
            "land_cost": round(sum(l[2] for l in r["land"][p])),
            "first_sell_day": r["first_sell_day"][p],
            "market_ops": r["market_ops"][p],
            "unit_ops": r["unit_ops"][p],
            "money_traj": [round(m) for m in r["money"][p][::24]],
            "n_steps_acted": len(r["money"][p]),
        })
    return out


def do_replay(path):
    ep = os.path.basename(path).split("-")[1]
    dst = os.path.join(OUT, ep + ".json")
    if os.path.exists(dst):
        return dst
    from src.replay_mine import mine
    r = mine(path, verbose=False)
    os.makedirs(OUT, exist_ok=True)
    with open(dst, "w") as f:
        json.dump(features(r), f)
    return dst


if __name__ == "__main__":
    args = sys.argv[1:]
    for a in args:
        for p in sorted(glob.glob(a)):
            try:
                print("ok", do_replay(p), flush=True)
            except Exception as e:
                print("ERR", p, type(e).__name__, e, flush=True)
