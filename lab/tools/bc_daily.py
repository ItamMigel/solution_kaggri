"""Export per-episode × player × day control trajectories from census fp (v2) → JSONL for RL/BC.
Row: {episode, player, name, day, hands, herd{COW,SHEEP,GOOSE}, plants{crop:n}, weeds, empty, locked, shops, money,
      final, opp_final, margin, won, source}.  usage: python bc_daily.py"""
import glob, json, os
OUT = "/workspace/shared/research/bc_daily"; os.makedirs(OUT, exist_ok=True)
for src, d in [("top", "/workspace/shared/research/census/fp"), ("ours", "/workspace/shared/research/census_ours/fp")]:
    n = 0
    with open(f"{OUT}/{src}.jsonl", "w") as f:
        for fn in glob.glob(d + "/*.json"):
            e = json.load(open(fn))
            if e.get("v") != 2: continue
            for p in range(2):
                me, op = e["players"][p], e["players"][1 - p]
                for day in e["daily"]:
                    t = day["tiles"][p]
                    f.write(json.dumps({"source": src, "episode": e["episode"], "player": p, "name": me["name"], "day": day["day"],
                        "hands": day["hands"][p], "herd": {k: t.get("A_" + k, 0) for k in ("COW", "SHEEP", "GOOSE")},
                        "plants": {k[2:]: v for k, v in t.items() if k.startswith("P_")}, "weeds": t.get("WEED", 0),
                        "empty": t.get("EMPTY", 0), "locked": t.get("LOCKED", 0), "shops": day["shops"],
                        "money": me["money_by_day"][min(day["day"], 29)], "final": me["final"], "opp_final": op["final"],
                        "margin": me["final"] - op["final"], "won": me["final"] > op["final"]}) + "\n"); n += 1
    print(src, n, "rows")
