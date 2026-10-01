"""Representation ceiling of the BC action codec (lab/bc/feat.py + lab/bc/export.py).

Re-plays a recorded Kaggle episode in the official engine with the recorded seed, both players following
their recorded action tapes, but the EXPERT's actions are passed through the BC codec first:
  identity  - no change (sanity: must reproduce the recorded rewards exactly)
  market    - market orders -> feat.encode_market -> export._market (per-key counts, fixed order, no NOOP slots)
  units     - unit actions -> feat.encode_unit_action -> export._unit_triple (heuristic PICKUP/PLACE quantities)
  both      - market + units
The loss in the expert's final money vs identity is what the BC representation cannot express, before any learning.
The tape stays open-loop, so later divergence is part of the measured damage.

usage: python codec_ceiling.py --glob '../../replays/56521745/*.gz' --team Boey --variants identity,market,units,both \
           --out ../../runs/codec/boey.jsonl --workers 24
"""
import argparse, contextlib, glob, gzip, io, json, os, sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "bc"))
import feat  # noqa: E402

ANIMALS = feat.ANIMALS
# ---- verbatim copies of the decoding helpers in lab/bc/export.py RUNTIME (what the BC agent executes) ----
_PICK_N = {"FERTILIZER": 4}


def _unit_triple(k, inv, shed_left):
    if ":" not in k: return [k]
    op, it = k.split(":")
    if op == "PLANT": return ["PLANT", it]
    if op == "PICKUP":
        n = 1 if it in ANIMALS else _PICK_N.get(it, 3)
        n = max(1, min(n, int(shed_left.get(it, 0)))); shed_left[it] = shed_left.get(it, 0) - n
        return ["PICKUP", it, n]
    n = 1 if (it in ANIMALS or it == "FERTILIZER") else max(1, int((inv or {}).get(it, 1)))
    return ["PLACE", it, n]


_MKT_ORDER_IDX = [feat.MKT_IDX[k] for k in feat.MKT_ORDER]


def _market(q):
    out = []
    for k in _MKT_ORDER_IDX:
        key = feat.MKT_KEYS[k]; n = int(q[k]); op, _, it = key.partition(":")
        if n <= 0: continue
        if op in ("HIRE", "BUY_LAND"):
            out += [[op]] * min(n, 10)
        elif op == "BUY_ANIMAL":
            out += [[op, it, 1]] * min(n, 10)
        else:
            out.append([op, it, n])
    return out[:10]
# -----------------------------------------------------------------------------------------------------------


def _get(o, k, default=None):
    try:
        v = o.get(k, default)
    except AttributeError:
        v = getattr(o, k, default)
    return default if v is None else v


MKT_SEQ_QMAX = 40


def market_seq(orders, qmax=MKT_SEQ_QMAX):
    """Proposed lossless-ish market codec: keep the ordered slot sequence (incl. NOOP slots), clip qty to qmax."""
    out = []
    for o in (orders or [])[:10]:
        if not isinstance(o, list) or not o:
            out.append(["NOOP"]); continue
        if o[0] in ("SELL", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL") and len(o) > 2:
            out.append([o[0], o[1], max(1, min(int(o[2]), qmax))])
        elif o[0] in ("HIRE", "BUY_LAND"):
            out.append([o[0]])
        else:
            out.append(["NOOP"])
    return out


def units_exactqty(a, obs):
    """Op class through the BC vocabulary, but PICKUP/PLACE keep the expert's quantity (a qty head would learn it)."""
    units = [a.get("farmer")] + list(a.get("hands") or [])
    out = []
    for u in units:
        k = feat.UNIT_OPS[feat.encode_unit_action(u)]
        if ":" in k and u and len(u) > 2:
            op, it = k.split(":"); out.append([op, it, int(u[2])])
        elif ":" in k:
            op, it = k.split(":"); out.append([op, it] if op == "PLANT" else [op, it, 1])
        else:
            out.append([k])
    a["farmer"] = out[0] if out else ["PASS"]; a["hands"] = out[1:]
    return a


def transform(action, obs, variant):
    a = dict(action or {})
    if variant in ("mseq", "v3"):
        a["market"] = market_seq(a.get("market"))
    if variant in ("uqty", "v3"):
        a = units_exactqty(a, obs)
    if variant in ("market", "both"):
        a["market"] = _market(feat.encode_market(a.get("market")))
    if variant in ("units", "both"):
        priv = _get(obs, "private", {}) or {}
        invs = list(_get(priv, "inventories", []) or [])
        shed_left = {it: int((_get(priv, "shed", {}) or {}).get(it, 0)) for it in feat.ITEMS}
        units = [a.get("farmer")] + list(a.get("hands") or [])
        out = []
        for i, u in enumerate(units):
            k = feat.UNIT_OPS[feat.encode_unit_action(u)]
            out.append(_unit_triple(k, invs[i] if i < len(invs) else {}, shed_left))
        a["farmer"] = out[0] if out else ["PASS"]; a["hands"] = out[1:]
    return a


CANON_DIR = os.environ.get("CANON_DIR", "")


def tape_agent(tape, variant):
    state = {"n": 0}

    def agent(obs, config=None):
        k = _get(obs, "step", None)
        k = state["n"] if k is None else int(k)
        state["n"] = k + 1
        act = tape[k] if k < len(tape) else None
        return transform(act, obs, variant) if variant != "identity" else (act or {})
    return agent


def job(args):
    path, team, variant = args
    from kaggle_environments import make
    d = json.load(gzip.open(path, "rt") if path.endswith(".gz") else open(path))
    names = d["info"]["TeamNames"]
    if team not in names:
        return {"file": path, "variant": variant, "error": "team_not_in_episode"}
    p = names.index(team); seed = d["info"]["seed"]
    tapes = [[d["steps"][k + 1][s]["action"] for k in range(len(d["steps"]) - 1)] for s in (0, 1)]
    cfg = {k: v for k, v in d["configuration"].items() if k not in ("agents", "seed")}; cfg["seed"] = seed
    if variant.startswith("canon"):
        cj = json.load(open(os.path.join(CANON_DIR, os.path.basename(path).replace("-replay.json.gz", ".json"))))
        for s in (0, 1):  # both players use canonical (execution-equivalent) markets
            tapes[s] = [dict(a or {}, market=cj["canon"][s][k]) for k, a in enumerate(tapes[s])]
        if variant == "canon_nonoop":
            tapes[p] = [dict(a, market=[o for o in a["market"] if o != ["NOOP"]]) for a in tapes[p]]
    label = variant
    if variant.startswith("canon"):
        variant = "identity"
    agents = [tape_agent(tapes[s], variant if s == p else "identity") for s in (0, 1)]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        env = make("kaggriculture", configuration=cfg, debug=False)
        env.run(agents)
    r = [s.reward for s in env.state]
    rec = d["rewards"]
    return {"file": os.path.basename(path), "episode": d["info"]["EpisodeId"], "team": team, "seat": p,
            "opponent": names[1 - p], "variant": label, "rec_self": rec[p], "rec_opp": rec[1 - p],
            "sim_self": r[p], "sim_opp": r[1 - p], "status": [s.status for s in env.state]}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--glob", required=True); ap.add_argument("--team", required=True)
    ap.add_argument("--variants", default="identity,market,units,both"); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", required=True); ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(); os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    files = sorted(glob.glob(a.glob))
    if a.limit: files = files[: a.limit]
    jobs = [(f, a.team, v) for f in files for v in a.variants.split(",")]
    with ProcessPoolExecutor(a.workers) as ex, open(a.out, "w") as fo:
        for res in ex.map(job, jobs):
            fo.write(json.dumps(res) + "\n"); fo.flush()
    print("wrote", len(jobs), "rows to", a.out)


if __name__ == "__main__":
    main()
