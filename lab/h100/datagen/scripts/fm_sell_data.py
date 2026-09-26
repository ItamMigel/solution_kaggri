"""Per-turn SELL quantities of top teams (requested orders) + conditioning features, for conditional flow matching."""
import gzip, json, sys, numpy as np
R = "/workspace/shared/research/re"; ITEMS = ["WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER"]
SHOPS = ["BAKERY","PIZZA_SHOP","BRUNCH_SPOT","YARN_STORE","ICE_CREAM_SHOP","PET_CAFE","SMOOTHIE_SHOP","FARMERS_MARKET"]
X, C = [], []
for tag in sys.argv[2:]:
    for l in gzip.open(f"{R}/{tag}.jsonl.gz", "rt"):
        r = json.loads(l)
        stock = [r["shed"].get(i, 0) + r["carried"].get(i, 0) for i in ITEMS]
        sell = [0.0] * len(ITEMS)
        for o in r["market"]:
            if o and o[0] == "SELL" and len(o) > 2 and o[1] in ITEMS: sell[ITEMS.index(o[1])] += float(o[2])
        frac = [min(1.0, s / st) if st > 0 else 0.0 for s, st in zip(sell, stock)]      # fraction of stock sold this turn
        cond = [r["hour"] / 23.0, r["day"] / 29.0] + [np.log1p(s) for s in stock] + [r["prices"][i] / 100.0 for i in ITEMS] + \
               [(r["inv"][i] - 10000) / 100.0 for i in ITEMS] + [sum(1 for s in r["shops"] if s == k) for k in SHOPS] + \
               [np.log1p(max(0, r["op"]["money"])), r["op"]["animals"].get("COW", 0), r["op"]["animals"].get("SHEEP", 0), r["op"]["animals"].get("GOOSE", 0),
                r["op"]["tiles"].get("plant_STRAWBERRY", 0), r["op"]["tiles"].get("plant_MELON", 0)]
        if sum(stock) == 0: continue
        X.append(frac); C.append(cond)
X, C = np.array(X, np.float32), np.array(C, np.float32); np.savez(sys.argv[1], x=X, c=C, items=np.array(ITEMS)); print("rows", len(X), "cond", C.shape[1])
