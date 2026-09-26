"""Day-level macro transitions of top teams for conditional flow matching.
x_d = macro state at hour 2 of day d; target = x_{d+1}; condition = (x_d, day, shop counts, opponent macro).
usage: python fm_data.py out.npz boey mmpq dsm fourthq decem mgoose fuxi"""
import gzip, json, sys
import numpy as np
R = "/workspace/shared/research/re"; CROPS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"]; AN = ["COW", "SHEEP", "GOOSE"]
SHOPS = ["BAKERY", "PIZZA_SHOP", "BRUNCH_SPOT", "YARN_STORE", "ICE_CREAM_SHOP", "PET_CAFE", "SMOOTHIE_SHOP", "FARMERS_MARKET"]
def macro(m):
    return [m["tiles"].get("plant_" + c, 0) for c in CROPS] + [m["animals"].get(a, 0) for a in AN] + \
           [m["structs"].get("PASTURE", 0), m["structs"].get("COOP", 0), m["quads"], m["hands"], np.log1p(max(0, m["money"])), m["fert_tiles"], m["tiles"].get("empty", 0)]
NAMES = [f"tile_{c}" for c in CROPS] + [f"n_{a}" for a in AN] + ["pasture", "coop", "quads", "hands", "log_money", "fert_tiles", "empty"]
if __name__ == "__main__":
    X, C, Y, T = [], [], [], []
    for tag in sys.argv[2:]:
        ep = {}
        for l in gzip.open(f"{R}/{tag}.jsonl.gz", "rt"):
            r = json.loads(l)
            if r["hour"] != 2: continue
            shops = [sum(1 for s in r["shops"] if s == k) for k in SHOPS]
            ep.setdefault(r["ep"], {})[r["day"]] = (macro(r["me"]), macro(r["op"]), shops, r["reward"] > r["opp_reward"])
        for e, days in ep.items():
            for d in sorted(days):
                if d + 1 not in days: continue
                me, op, shops, won = days[d]
                X.append(me); Y.append(days[d + 1][0]); C.append([d / 29.0] + shops + op); T.append(tag)
    X, Y, C = np.array(X, np.float32), np.array(Y, np.float32), np.array(C, np.float32)
    np.savez(sys.argv[1], x=X, y=Y, c=C, tag=np.array(T), names=np.array(NAMES)); print("transitions", len(X), "dims", X.shape[1], "cond", C.shape[1])
