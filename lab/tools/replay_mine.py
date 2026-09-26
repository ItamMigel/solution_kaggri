"""Mine a Kaggle replay by re-running it bit-exactly in the real engine with
instrumentation on _commit_unit / _do_hire / _do_buy_land / unit actions.

Usage: python -m src.replay_mine replays_top/episode-XXXX-replay.json [--json out.json]
"""
import gzip
import json
import sys
from collections import Counter, defaultdict

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as K


def mine(path, verbose=True):
    _open = gzip.open if path.endswith(".gz") else open
    with _open(path, "rt") as _f:
        d = json.load(_f)
    cfg = dict(d["configuration"])
    cfg["seed"] = d["info"]["seed"]
    names = d["info"].get("TeamNames", ["p0", "p1"])
    steps = d["steps"]

    # ---- instrumentation state -------------------------------------------
    cur = {"step": 0, "day": 0}
    farms_ref = {}
    sells = [defaultdict(lambda: [0, 0.0]), defaultdict(lambda: [0, 0.0])]  # item -> [units, revenue]
    buys = [defaultdict(lambda: [0, 0.0]), defaultdict(lambda: [0, 0.0])]
    sell_by_day = [defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))]
    sell_price_by_day = [defaultdict(list), defaultdict(list)]
    hires = [Counter(), Counter()]  # day -> n
    hire_cost = [0.0, 0.0]
    land = [[], []]
    unit_ops = [Counter(), Counter()]
    unit_ops_ok = [Counter(), Counter()]
    market_ops = [Counter(), Counter()]
    order_lane = [Counter(), Counter()]  # (op, index) counts
    first_sell_day = [{}, {}]
    # Per-day wheat-flow instrumentation is deliberately action-success based.
    # End-of-day tile snapshots alone cannot distinguish a crop that was grown
    # and harvested from a crop never planted at all.
    wheat_daily = [defaultdict(Counter), defaultdict(Counter)]
    wheat_state = [[], []]

    orig_commit = K._commit_unit
    orig_hire = K._do_hire
    orig_land = K._do_buy_land
    orig_unit = K._apply_unit_action

    def commit(op, item, price, farm, private, market, *extra):
        pid = farms_ref.get(id(farm), 0)
        ok = orig_commit(op, item, price, farm, private, market, *extra)
        if ok:
            day = cur["day"]
            if op == "SELL":
                sells[pid][item][0] += 1
                sells[pid][item][1] += price
                sell_by_day[pid][day][item] += 1
                sell_price_by_day[pid][day].append((item, price))
                first_sell_day[pid].setdefault(item, day)
            elif op in ("BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL"):
                key = op + ":" + item
                buys[pid][key][0] += 1
                buys[pid][key][1] += price
                if item == "WHEAT" and op in ("BUY_PRODUCT", "BUY_SEED"):
                    prefix = "buy_product" if op == "BUY_PRODUCT" else "buy_seed"
                    wheat_daily[pid][day][prefix + "_wheat_units"] += 1
                    wheat_daily[pid][day][prefix + "_wheat_cost"] += price
                if op == "BUY_PRODUCT":
                    sell_by_day[pid][day]["BUY_" + item] -= 1
                    sell_price_by_day[pid][day].append(("BUY_" + item, price))
        return ok

    def hire(farm, private, board_size, mult):
        pid = farms_ref.get(id(farm), 0)
        before = farm["money"]
        n0 = len(farm["hands"])
        orig_hire(farm, private, board_size, mult)
        if len(farm["hands"]) > n0:
            hires[pid][cur["step"] // 24] += 1
            hire_cost[pid] += before - farm["money"]

    def buyland(farm, board_size):
        pid = farms_ref.get(id(farm), 0)
        n0 = len(farm["unlocked_quadrants"])
        before = farm["money"]
        orig_land(farm, board_size)
        if len(farm["unlocked_quadrants"]) > n0:
            land[pid].append((cur["step"] // 24, farm["unlocked_quadrants"][-1], before - farm["money"]))

    def unit(farm, private, idx, action, board_size, day, turns_per_day, shed_capacity=100):
        pid = farms_ref.get(id(farm), 0)
        op = action[0] if isinstance(action, list) and action else "?"
        unit_ops[pid][op] += 1
        pos = _farmer_pos(farm, idx)
        tile_before = None
        if pos is not None:
            x, y = pos
            tile = farm["tiles"][y][x]
            if isinstance(tile, dict):
                # Only scalar fields are used below; do not retain a mutable
                # reference which _apply_unit_action changes in-place.
                tile_before = dict(tile)
        inv_before_wheat = private["inventories"][idx].get("WHEAT", 0) if idx < len(private["inventories"]) else 0
        snap = (farm["money"], json.dumps(private["shed"], sort_keys=True),
                str(_farmer_pos(farm, idx)), json.dumps(private["inventories"], sort_keys=True))
        orig_unit(farm, private, idx, action, board_size, day, turns_per_day, shed_capacity)
        snap2 = (farm["money"], json.dumps(private["shed"], sort_keys=True),
                 str(_farmer_pos(farm, idx)), json.dumps(private["inventories"], sort_keys=True))
        # crude but sufficient: tile mutations not caught -> handle separately
        if snap != snap2:
            unit_ops_ok[pid][op] += 1
        if pos is not None:
            x, y = pos
            tile_after = farm["tiles"][y][x]
            if op == "PLANT" and len(action) >= 2 and action[1] == "WHEAT":
                if isinstance(tile_after, dict) and tile_after.get("kind") == "PLANT" and tile_after.get("crop") == "WHEAT":
                    wheat_daily[pid][day]["wheat_tiles_planted"] += 1
            elif op == "HARVEST" and tile_before and tile_before.get("kind") == "PLANT" and tile_before.get("crop") == "WHEAT":
                # A successful harvest clears yield_units (and removes a
                # finite crop); record both the tile action and yielded units.
                yielded = tile_before.get("yield_units", 0)
                after_yield = tile_after.get("yield_units", 0) if isinstance(tile_after, dict) else 0
                if yielded > 0 and after_yield == 0:
                    wheat_daily[pid][day]["wheat_tiles_harvested"] += 1
                    wheat_daily[pid][day]["wheat_units_harvested"] += yielded
            elif op == "FEED" and tile_before and "animal" in tile_before:
                inv_after_wheat = private["inventories"][idx].get("WHEAT", 0) if idx < len(private["inventories"]) else 0
                if inv_after_wheat == inv_before_wheat - 1:
                    wheat_daily[pid][day]["feed_actions"] += 1
                    wheat_daily[pid][day]["wheat_units_fed"] += 1

    def _farmer_pos(farm, idx):
        return farm["farmer"] if idx == 0 else (farm["hands"][idx - 1] if idx - 1 < len(farm["hands"]) else None)

    orig_interp = K.interpreter

    def interp(state, env):
        fs = state[0].observation.farms
        farms_ref.clear()
        for i, f in enumerate(fs):
            farms_ref[id(f)] = i
        return orig_interp(state, env)

    K._commit_unit = commit
    K._do_hire = hire
    K._do_buy_land = buyland
    K._apply_unit_action = unit
    K.interpreter = interp
    import kaggle_environments as _ke
    _ke.core.environments["kaggriculture"]["interpreter"] = interp

    try:
        env = make("kaggriculture", configuration=cfg, debug=False)
        env.reset(2)

        money = [[], []]
        tiles_hist = []
        for t in range(1, len(steps)):
            cur["step"] = t
            before_obs = env.state[0]["observation"]
            cur["day"] = before_obs["day"]
            f0 = before_obs["farms"]
            farms_ref.clear()
            farms_ref[id(f0[0])] = 0
            farms_ref[id(f0[1])] = 1
            # Ladder replays may encode a timed-out/no-op turn as `"action": null`.
            # The engine accepts the equivalent empty action object.
            acts = [steps[t][p].get("action") or {} for p in range(2)]
            for p in range(2):
                m = acts[p].get("market") or []
                for i, o in enumerate(m[:10]):
                    if isinstance(o, list) and o:
                        market_ops[p][o[0]] += 1
                        order_lane[p][(o[0], i)] += 1
            env.step(acts)
            obs = env.steps[-1][0]["observation"]
            for p in range(2):
                money[p].append(obs["farms"][p]["money"])
            if t % 24 == 0 or t == len(steps) - 1:
                tiles_hist.append((t // 24, [_tile_census(obs["farms"][p]) for p in range(2)],
                                   dict(obs["market"]["prices"]),
                                   {k: 10000 - v for k, v in obs["market"]["inventory"].items()},
                                   [len(obs["farms"][p]["hands"]) for p in range(2)],
                                   [list(obs["farms"][p]["unlocked_quadrants"]) for p in range(2)],
                                   list(obs["town"]["unlocked_shops"])))
                for p in range(2):
                    census = _tile_census(obs["farms"][p])
                    # step 24 is the end of playable day 0 (the observation
                    # has already advanced to day 1), hence this label.
                    wheat_state[p].append({"day": (t - 1) // 24,
                                           "wheat_tiles_eod": census.get("P_WHEAT", 0),
                                           "hands_eod": len(obs["farms"][p]["hands"]),
                                           "quadrants_eod": len(obs["farms"][p]["unlocked_quadrants"])})
    finally:
        K._commit_unit = orig_commit
        K._do_hire = orig_hire
        K._do_buy_land = orig_land
        K._apply_unit_action = orig_unit

    res = {
        "episode": d["id"], "names": names, "rewards": d["rewards"], "seed": cfg["seed"],
        "sells": [{k: v for k, v in s.items()} for s in sells],
        "buys": [{k: v for k, v in b.items()} for b in buys],
        "hires": [dict(h) for h in hires], "hire_cost": hire_cost,
        "land": land,
        "unit_ops": [dict(u) for u in unit_ops], "unit_ops_ok": [dict(u) for u in unit_ops_ok],
        "market_ops": [dict(m) for m in market_ops],
        "order_lane": [{f"{k[0]}@{k[1]}": v for k, v in o.items()} for o in order_lane],
        "first_sell_day": first_sell_day,
        "money": money,
        "tiles_hist": tiles_hist,
        "sell_by_day": [{d_: dict(v) for d_, v in s.items()} for s in sell_by_day],
        "sell_price_by_day": [{d_: v for d_, v in s.items()} for s in sell_price_by_day],
        "wheat_daily": [{d_: dict(v) for d_, v in days.items()} for days in wheat_daily],
        "wheat_state": wheat_state,
    }
    if verbose:
        report(res)
    return res


def _tile_census(farm):
    c = Counter()
    for row in farm["tiles"]:
        for tl in row:
            if tl is None:
                c["EMPTY"] += 1
            elif tl == "LOCKED":
                c["LOCKED"] += 1
            elif isinstance(tl, dict):
                if tl.get("kind") == "PLANT":
                    c["P_" + tl["crop"]] += 1
                elif tl.get("kind") == "WEED":
                    c["WEED"] += 1
                elif tl.get("animal"):
                    c["A_" + tl["animal"]] += 1
                else:
                    c["B_" + str(tl.get("kind"))] += 1
    return dict(c)


def report(r):
    print(f"=== episode {r['episode']} seed={r['seed']} ===")
    for p in range(2):
        print(f"\n--- P{p} {r['names'][p]}  FINAL ${r['rewards'][p]:,.0f} ---")
        s = r["sells"][p]
        tot = sum(v[1] for v in s.values())
        print(f"  REVENUE ${tot:,.0f}")
        for k, v in sorted(s.items(), key=lambda kv: -kv[1][1]):
            print(f"    {k:11s} {v[0]:5d} u  ${v[1]:10,.0f}   avg ${v[1]/max(1,v[0]):7.1f}  first sell d{r['first_sell_day'][p].get(k)}")
        b = r["buys"][p]
        tb = sum(v[1] for v in b.values()) + r["hire_cost"][p] + sum(l[2] for l in r["land"][p])
        print(f"  COSTS ${tb:,.0f}  (hires ${r['hire_cost'][p]:,.0f}, land ${sum(l[2] for l in r['land'][p]):,.0f})")
        for k, v in sorted(b.items(), key=lambda kv: -kv[1][1]):
            print(f"    buy {k:11s} {v[0]:5d} u  ${v[1]:10,.0f}")
        print(f"  land: {r['land'][p]}")
        hs = r["hires"][p]
        print(f"  hires by day: {dict(sorted(hs.items()))} total {sum(hs.values())}")
        print(f"  market ops: {r['market_ops'][p]}")
        print(f"  order lanes: {dict(sorted(r['order_lane'][p].items()))}")
        print(f"  unit ops: {dict(sorted(r['unit_ops'][p].items(), key=lambda kv:-kv[1]))}")


if __name__ == "__main__":
    mine(sys.argv[1])
