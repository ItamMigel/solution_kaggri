"""Canonical (execution-equivalent) market tapes.
Re-simulates a replay with both recorded tapes while instrumenting the engine's market processing, then rewrites
each player's market list: SELL/BUY_* orders that filled 0 units -> NOOP, partially filled -> filled quantity,
unknown ops -> NOOP, trailing NOOPs dropped. HIRE/BUY_LAND are kept as issued.
Verification: re-running the canonical tapes must reproduce the recorded rewards exactly.

usage: python canon_market.py --glob '../../../replays/56521745/*.gz' --out ../../../canon/56521745 --workers 24
Writes <out>/<episode>.json = {"episode", "seed", "canon": [tape_p0_market, tape_p1_market], "verified": bool, stats}"""
import argparse, contextlib, glob, gzip, io, json, os
from concurrent.futures import ProcessPoolExecutor


def simulate(d, market_override=None, instrument=False):
    from kaggle_environments import make
    import kaggle_environments.envs.kaggriculture.kaggriculture as K
    tapes = [[d["steps"][k + 1][s]["action"] for k in range(len(d["steps"]) - 1)] for s in (0, 1)]
    if market_override is not None:
        tapes = [[dict(a or {}, market=market_override[s][k]) for k, a in enumerate(tapes[s])] for s in (0, 1)]
    log = []  # per market call: list of (player, slot, order, ostate)
    orig_pm, orig_po = K._process_market, K._parse_order
    cur = {"calls": None, "counts": None, "queues": None}

    def parse(order):
        o = orig_po(order)
        if cur["calls"] is not None:
            # _process_market parses slot i for player 0 then player 1 (only players with a slot i)
            cur["calls"].append((order, o))
        return o

    def pm(state, env):
        cur["calls"] = []
        orig_pm(state, env)
        log.append(cur["calls"]); cur["calls"] = None

    if instrument:
        K._process_market, K._parse_order = pm, parse
    try:
        cfg = {k: v for k, v in d["configuration"].items() if k not in ("agents", "seed")}; cfg["seed"] = d["info"]["seed"]

        def mk(s):
            def ag(obs, config=None):
                k = int(obs.get("step", 0)); return tapes[s][k] if k < len(tapes[s]) else {}
            return ag
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            env = make("kaggriculture", configuration=cfg, debug=False); env.run([mk(0), mk(1)])
    finally:
        K._process_market, K._parse_order = orig_pm, orig_po
    return env, tapes, log


def canon_one(args):
    path, out = args
    dst = os.path.join(out, os.path.basename(path).replace("-replay.json.gz", ".json"))
    if os.path.exists(dst):
        return "skip"
    d = json.load(gzip.open(path, "rt"))
    env, tapes, log = simulate(d, instrument=True)
    rec = d["rewards"]
    if [s.reward for s in env.state] != rec:
        return f"ERR not reproducing {path}"
    maxo = int(d["configuration"].get("maxMarketOrdersPerTurn", 10))
    canon = [[None] * len(tapes[0]) for _ in (0, 1)]
    stats = {"orders": 0, "noop_in": 0, "failed": 0, "partial": 0}
    assert len(log) == len(tapes[0]), (len(log), len(tapes[0]))
    for k, calls in enumerate(log):
        queues = [list(((tapes[s][k] or {}).get("market") or []))[:maxo] for s in (0, 1)]
        # reconstruct (player, slot) for each parse call: slot-major, player-minor, only where slot exists
        order_seq = [(s, i) for i in range(max(len(q) for q in queues) if any(queues) else 0) for s in (0, 1) if i < len(queues[s])]
        assert len(order_seq) == len(calls), (k, len(order_seq), len(calls))
        res = {(s, i): o for (s, i), (_order, o) in zip(order_seq, calls)}
        for s in (0, 1):
            new = []
            for i, order in enumerate(queues[s]):
                stats["orders"] += 1
                o = res[(s, i)]
                if o is None:
                    stats["noop_in"] += 1; new.append(["NOOP"]); continue
                if o["type"] in ("HIRE", "BUY_LAND"):
                    new.append([o["type"]]); continue
                n = int(order[2]); filled = n - int(o["remaining"])
                if filled <= 0:
                    stats["failed"] += 1; new.append(["NOOP"])
                else:
                    stats["partial"] += filled < n; new.append([order[0], order[1], filled])
            while new and new[-1] == ["NOOP"]:
                new.pop()
            canon[s][k] = new
    env2, _, _ = simulate(d, market_override=canon)
    ok = [s.reward for s in env2.state] == rec
    json.dump({"episode": d["info"]["EpisodeId"], "names": d["info"]["TeamNames"], "canon": canon, "verified": ok, "stats": stats},
              open(dst, "w"))
    return f"ok verified={ok} {json.dumps(stats)}"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--glob", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=16); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    fs = sorted(glob.glob(a.glob))
    if a.limit:
        fs = fs[: a.limit]
    with ProcessPoolExecutor(a.workers) as ex:
        res = list(ex.map(canon_one, [(f, a.out) for f in fs]))
    import collections
    print(collections.Counter(r.split(" ")[0] + " " + (r.split(" ")[1] if len(r.split(" ")) > 1 else "") for r in res))
    print([r for r in res if r.startswith("ERR")][:3])
    tot = collections.Counter()
    for r in res:
        if r.startswith("ok"):
            tot.update(json.loads(r.split(" ", 2)[2]))
    print("totals:", dict(tot))


if __name__ == "__main__":
    main()
