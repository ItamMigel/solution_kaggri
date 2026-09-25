"""Per-day farm composition: BC agent (closed loop, from step 0) vs the recorded expert in the same world.
usage: python farmstats.py --ckpt ../../../bc3_runs/boey_r2/best.pt --replay <episode.json.gz> --team Boey [--persist]"""
import argparse, collections, contextlib, gzip, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "bc3"))


def farm_stats(o, p, hires_today=None):
    f = o["farms"][p]; an = collections.Counter(); pl = collections.Counter(); struct = collections.Counter(); weeds = 0
    for row in f["tiles"]:
        for t in row:
            if isinstance(t, dict):
                if t.get("kind") == "PLANT": pl[t.get("crop")] += 1
                elif t.get("kind") in ("COOP", "PASTURE"):
                    struct[t["kind"]] += 1
                    if t.get("animal"): an[t["animal"]] += 1
                elif t.get("kind") == "WEED": weeds += 1
    return dict(money=round(f["money"]), hands=len(f.get("hands") or []), hires=f.get("hires_today", 0), quads=len(f.get("unlocked_quadrants") or []),
                cow=an["COW"], sheep=an["SHEEP"], goose=an["GOOSE"], coop=struct["COOP"], pasture=struct["PASTURE"],
                wheat=pl["WHEAT"], carrot=pl["CARROT"], tomato=pl["TOMATO"], straw=pl["STRAWBERRY"], melon=pl["MELON"], weeds=weeds)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ckpt", required=True); ap.add_argument("--replay", required=True)
    ap.add_argument("--team", required=True); ap.add_argument("--persist", action="store_true"); ap.add_argument("--hour", type=int, default=22)
    ap.add_argument("--days", default="0,1,2,3,4,5,6,8,10,12,15,20,25,29")
    a = ap.parse_args()
    from kaggle_environments import make
    import agent3
    d = json.load(gzip.open(a.replay, "rt")); names = d["info"]["TeamNames"]; p = names.index(a.team)
    tapes = [[d["steps"][k + 1][s]["action"] for k in range(len(d["steps"]) - 1)] for s in (0, 1)]
    cfg = {k: v for k, v in d["configuration"].items() if k not in ("agents", "seed")}; cfg["seed"] = d["info"]["seed"]
    bc = agent3.Agent(os.path.abspath(a.ckpt), persist=a.persist)

    def opp(obs, config=None):
        k = int(obs.get("step", 0)); return tapes[1 - p][k] if k < len(tapes[1 - p]) else {}
    agents = [bc, opp] if p == 0 else [opp, bc]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        env = make("kaggriculture", configuration=cfg, debug=False); env.run(agents)
    print(f"episode {d['info']['EpisodeId']} {a.team} seat {p} vs {names[1 - p]}; final BC {env.state[p].reward} vs rec {d['rewards'][p]}")
    keys = ["money", "hands", "quads", "cow", "sheep", "goose", "wheat", "carrot", "tomato", "straw", "melon", "weeds"]
    print("day  " + "  ".join(f"{k:>11}" for k in keys) + "    (BC / expert)")
    for day in [int(x) for x in a.days.split(",")]:
        t = min(24 * day + a.hour, len(d["steps"]) - 1)
        rec = farm_stats(d["steps"][t][0]["observation"], p); sim = farm_stats(env.steps[t][0].observation, p)
        print(f"{day:3}  " + "  ".join(f"{sim[k]:>5}/{rec[k]:<5}" for k in keys))


if __name__ == "__main__":
    main()
