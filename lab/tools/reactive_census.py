"""Daily, read-only census of named teams' Kaggriculture replay folders.

The replay includes every observation and action.  We re-run it through the
official engine for successful hires, land purchases, and exact market sale
prices, then take end-of-day farm snapshots directly from the replay.  The
output preserves both sides of each episode: a reactive agent must be compared
with the opponent it actually faced, rather than with an invented fixed bot.

Example:
  python lab/tools/reactive_census.py --root /workspace/shared/replays/reactive \
      --out /workspace/shared/research/t034_reactive --workers 8
"""
import argparse
import glob
import json
import multiprocessing as mp
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from replay_mine import mine

ANIMALS = ("COW", "SHEEP", "GOOSE")
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")


def _census_tiles(farm):
    counts = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict):
                if tile.get("kind") == "PLANT":
                    counts["crop_" + tile["crop"]] += 1
                elif tile.get("animal"):
                    counts["animal_" + tile["animal"]] += 1
    return {key: counts[key] for key in [*("animal_" + a for a in ANIMALS),
                                         *("crop_" + c for c in CROPS)]}


def _commands(action):
    if not isinstance(action, dict):
        return []
    return [action.get("farmer") or []] + list(action.get("hands") or [])


def _fertilizer_events(steps, player):
    """Per-day declared FERTILIZE actions.

    Replay action-array worker indices can be re-mapped by the engine before
    execution, so comparing a fixed private-inventory slot between frames is
    not a validity proof.  Successful total actions come from replay_mine's
    engine hook; this timeline is intentionally labelled *declared*.
    """
    out = Counter()
    for t in range(1, len(steps)):
        for actor, command in enumerate(_commands(steps[t][player].get("action") or {})):
            if command and command[0] == "FERTILIZE": out[t // 24] += 1
    return out


def _sale_rows(result, player):
    out = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
    # replay_mine instruments successful individual SELL commits.  Its price
    # trace has the exact commit order and shared-market price, unlike order
    # intent in a replay action.
    for day, pairs in result["sell_price_by_day"][player].items():
        for item, price in pairs:
            if not item.startswith("BUY_"):
                out[int(day)][item][0] += 1
                out[int(day)][item][1] += price
    return {d: {item: {"units": n, "revenue": rev, "mean_price": rev / n}
                for item, (n, rev) in rows.items()}
            for d, rows in out.items()}


def _one(path):
    with open(path) as f:
        replay = json.load(f)
    result = mine(path, verbose=False)
    names = replay["info"].get("TeamNames", ["p0", "p1"])
    days = []
    for player in range(2):
        fert = _fertilizer_events(replay["steps"], player)
        sales = _sale_rows(result, player)
        lands = defaultdict(list)
        for day, quadrant, cost in result["land"][player]:
            lands[int(day)].append({"quadrant": quadrant, "cost": cost})
        rows = []
        for day in range(30):
            # step 24 is state after playable day zero.  Final d29 has no
            # following observation; use the pre-final frame rather than
            # inventing a state from final rewards.
            step = min((day + 1) * 24, len(replay["steps"]) - 1)
            obs = replay["steps"][step][player].get("observation") or {}
            farm = (obs.get("farms") or [{}, {}])[player]
            rows.append({"day": day, "tiles": _census_tiles(farm),
                         "land_unlocked": list(farm.get("unlocked_quadrants") or []),
                         "land_events": lands.get(day, []),
                         "hires": int(result["hires"][player].get(day, 0)),
                         "fertilize_declared": int(fert.get(day, 0)),
                         "sales": sales.get(day, {}),
                         "money_eod": farm.get("money")})
        days.append(rows)
    return {"episode_id": replay.get("id"), "seed": replay["info"].get("seed"),
            "file": path, "names": names, "rewards": replay.get("rewards"),
            "players": days}


def _number(value):
    return value if isinstance(value, (int, float)) else 0


def _aggregate(records, target):
    # Aggregate target and actual opponent separately by day, averaging one
    # observation per episode (not over orders or individual games' players).
    total = {"episodes": len(records), "target": [], "opponent": [], "final_margin": []}
    for side in ("target", "opponent"):
        days = []
        for day in range(30):
            acc, n = defaultdict(float), 0
            sale = defaultdict(lambda: [0.0, 0.0])
            for r in records:
                p = r["names"].index(target)
                q = 1 - p
                x = r["players"][p if side == "target" else q][day]
                n += 1
                acc["hires"] += x["hires"]; acc["fertilize_declared"] += x["fertilize_declared"]
                acc["land_quadrants"] += len(x["land_unlocked"])
                for k, v in x["tiles"].items(): acc[k] += _number(v)
                for item, v in x["sales"].items():
                    sale[item][0] += v["units"]; sale[item][1] += v["revenue"]
            days.append({"day": day, "means": {k: v / max(n, 1) for k, v in acc.items()},
                         "sales": {k: {"units": v[0] / max(n, 1), "revenue": v[1] / max(n, 1),
                                        "mean_price": v[1] / v[0] if v[0] else None}
                                   for k, v in sale.items()}})
        total[side] = days
    for r in records:
        p = r["names"].index(target); q = 1 - p
        total["final_margin"].append(_number(r["rewards"][p]) - _number(r["rewards"][q]))
    total["mean_final_margin"] = sum(total["final_margin"]) / max(1, len(total["final_margin"]))
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    root, out = Path(args.root), Path(args.out); out.mkdir(parents=True, exist_ok=True)
    files = sorted(glob.glob(str(root / "*" / "episode-*-replay.json")))
    # A maximum of eight independent official-engine workers was predeclared
    # for T034; do not silently consume the host.
    with mp.Pool(processes=min(8, max(1, args.workers))) as pool:
        rows = list(pool.imap_unordered(_one, files))
    rows.sort(key=lambda r: (r["names"], r["episode_id"]))
    with open(out / "episodes.jsonl", "w") as f:
        for row in rows: f.write(json.dumps(row, ensure_ascii=False) + "\n")
    groups = defaultdict(list)
    for row in rows:
        for name in row["names"]:
            if (root / name.lower().replace(" ", "_")).exists(): groups[name].append(row)
    # Folder slugs are not reliable for Cyrillic team names; target matching is
    # instead explicit from each folder's first replay.
    groups.clear()
    for folder in root.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"): continue
        rfiles = {str(p) for p in folder.glob("episode-*-replay.json")}
        subset = [r for r in rows if r["file"] in rfiles]
        if subset:
            names = Counter(n for r in subset for n in r["names"])
            target = max(names, key=lambda n: sum(n in r["names"] for r in subset))
            # The submission owner's name appears in every replay; an opponent
            # almost never does.  Require full coverage to avoid false labels.
            for n in names:
                if all(n in r["names"] for r in subset): target = n; break
            groups[target] = subset
    summary = {target: _aggregate(rs, target) for target, rs in groups.items()}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({k: v["episodes"] for k, v in summary.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
