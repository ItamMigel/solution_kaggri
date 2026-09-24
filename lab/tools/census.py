"""Fingerprint every downloaded replay (both players) -> compact JSON per episode, then aggregate.
usage: python census.py mine --index /workspace/shared/replays/top/index.jsonl --out /workspace/shared/research/census --workers 16
       python census.py report --out /workspace/shared/research/census"""
import argparse, glob, json, os, sys
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict

def fp_one(path):
    from replay_mine import mine
    r = mine(path, verbose=False)
    out = {"episode": r["episode"], "names": r["names"], "rewards": r["rewards"], "seed": r["seed"], "players": []}
    for p in range(2):
        sells = {k: [v[0], round(v[1])] for k, v in r["sells"][p].items()}
        buys = {k: [v[0], round(v[1])] for k, v in r["buys"][p].items()}
        hands = [h[p] for (_, _, _, _, h, _, _) in r["tiles_hist"]]
        out["players"].append({
            "name": r["names"][p], "final": r["rewards"][p], "sells": sells, "buys": buys,
            "animals": {k.split(":")[1]: v[0] for k, v in buys.items() if k.startswith("BUY_ANIMAL")},
            "seeds": {k.split(":")[1]: v[0] for k, v in buys.items() if k.startswith("BUY_SEED")},
            "hire_cost": round(r["hire_cost"][p]), "hands_by_day": hands, "land": r["land"][p],
            "first_sell_day": r["first_sell_day"][p], "unit_ops": r["unit_ops"][p], "order_lane": r["order_lane"][p],
            "money_by_day": [r["money"][p][min(len(r["money"][p]) - 1, d * 24 + 23)] for d in range(30)],
        })
    out["shops"] = r["tiles_hist"][-1][6]
    out["daily"] = [{"day": day, "tiles": tiles, "hands": hands, "shops": shops} for (day, tiles, _pr, _inv, hands, _q, shops) in r["tiles_hist"]]
    out["v"] = 2
    return out

def _job(args):
    path, dst = args
    if os.path.exists(dst) and json.load(open(dst)).get("v") == 2: return "skip"
    try:
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            res = fp_one(path)
        json.dump(res, open(dst, "w")); return "ok"
    except Exception as e:
        return f"ERR {path}: {e!r}"

def cmd_mine(a):
    os.makedirs(a.out + "/fp", exist_ok=True)
    seen, jobs = set(), []
    for l in open(a.index):
        d = json.loads(l)
        if d["episode_id"] in seen or not os.path.exists(d["file"]): continue
        seen.add(d["episode_id"]); jobs.append((d["file"], f"{a.out}/fp/{d['episode_id']}.json"))
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(_job, jobs))
    print({k: sum(1 for r in res if r.startswith(k)) for k in ("ok", "skip", "ERR")})
    for r in res:
        if r.startswith("ERR"): print(r)


def cmd_report(a):
    import statistics as st
    rows = defaultdict(list)
    for f in glob.glob(a.out + "/fp/*.json"):
        d = json.load(open(f))
        for p in range(2):
            me, op = d["players"][p], d["players"][1 - p]
            rows[me["name"]].append((me, op, d))
    lines = ["| team | n | W-L | mean $ | mean opp $ | animals (c/s/g/ch) | straw seeds | melon | carrot | tomato | max hands | land days | top sells |", "|" + "---|" * 13]
    for name, lst in sorted(rows.items(), key=lambda kv: -st.mean(x[0]["final"] for x in kv[1])):
        if len(lst) < a.min_n: continue
        w = sum(me["final"] > op["final"] for me, op, _ in lst); l = sum(me["final"] < op["final"] for me, op, _ in lst)
        m = lambda f: st.mean(f(me) for me, _, _ in lst)
        an = lambda k: m(lambda me: me["animals"].get(k, 0))
        sd = lambda k: m(lambda me: me["seeds"].get(k, 0))
        rev = defaultdict(float)
        for me, _, _ in lst:
            for k, v in me["sells"].items(): rev[k] += v[1] / len(lst)
        top = ", ".join(f"{k[:5]} {v/1000:.0f}k" for k, v in sorted(rev.items(), key=lambda kv: -kv[1])[:5])
        lands = "/".join(f"{st.mean(x[0]['land'][i][0] for x in lst if len(x[0]['land']) > i):.0f}" for i in range(3) if any(len(x[0]['land']) > i for x in lst))
        lines.append(f"| {name[:24]} | {len(lst)} | {w}-{l} | {m(lambda me: me['final'])/1000:.0f}k | {st.mean(op['final'] for _, op, _ in lst)/1000:.0f}k | "
                     f"{an('COW'):.1f}/{an('SHEEP'):.1f}/{an('GOOSE'):.1f}/{an('CHICKEN'):.1f} | {sd('STRAWBERRY'):.0f} | {sd('MELON'):.0f} | {sd('CARROT'):.0f} | {sd('TOMATO'):.0f} | "
                     f"{m(lambda me: max(me['hands_by_day'])):.1f} | {lands} | {top} |")
    txt = "\n".join(lines); open(a.out + "/report.md", "w").write(txt + "\n"); print(txt)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd"); ap.add_argument("--index", default="/workspace/shared/replays/top/index.jsonl")
    ap.add_argument("--out", default="/workspace/shared/research/census"); ap.add_argument("--workers", type=int, default=16); ap.add_argument("--min-n", type=int, default=3)
    a = ap.parse_args(); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    {"mine": cmd_mine, "report": cmd_report}[a.cmd](a)
