"""CEM search for imitation fidelity.

Structural genes (herd, hands, quadrants, seed counts) are PINNED to the values measured
from the real replays -- they ARE the fingerprint and must match exactly.  Only execution
genes (task values, water/care/harvest weights, sell policy) are searched, with the
objective = weighted relative error against the real production fingerprint + final money.
"""
import json, os, sys, random, statistics as st, tempfile
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/workspace/kaggriculture")

from fit import TARGETS, KEYS  # noqa: E402

# execution genes searched: name -> (lo, hi, is_int)
SEARCH = {
    "water_gain_val": (60, 260), "water_idle_val": (0, 90),
    "care_val": (20, 110), "collect_val": (20, 110), "feed_val": (60, 180),
    "ahv_base": (30, 110), "ahv_mult": (3, 20), "chv_ong_mult": (5, 30),
    "dig_val": (20, 90), "pickup_w_val": (60, 200),
    "straw_fert_val": (100, 400), "fert_pickup_val": (0, 220),
    "move_cost": (2, 16), "azone_frac": (10, 34),
    "bundle_decay": (20, 95), "bundle_max": (1, 6),
    "straw_urgency": (100, 340), "urg_MELON": (60, 300),
    "sell_rate_pct": (60, 100), "shed_soft_cap": (4, 30),
    "minp_STRAWBERRY": (100, 200), "minp_MILK": (100, 200),
    "minp_WOOL": (100, 200), "minp_MELON": (100, 160),
    "melon_sell_cap": (60, 200), "hold_start_day": (0, 12), "hold_full_day": (8, 24),
    "wheat_keep_pct": (60, 400), "wheat_per_unit": (1, 8),
    "care_price_w": (0, 200), "collect_dyn": (0, 1), "care_skip_dead": (0, 1),
    # strawberry doubling depends on holding fertiliser back from the sell book and
    # watering on the production night -- both were missing from round 1
    "fert_reserve": (0, 40), "straw_water_val": (0, 200), "straw_fert_price_w": (0, 200),
    "max_shed_backlog": (1, 10), "harv_cap_bonus": (0, 40), "feed_smart": (0, 1),
    "plant_boost": (0, 40), "d0_seed_pct": (0, 100), "seed_front_days": (0, 6),
    # labour is left FREE: our planner is less efficient per hand than theirs, so pinning
    # hands to their 9.7 would pin our OUTPUT below theirs. Market fidelity (what our
    # candidate actually experiences) outranks structural fidelity on this one gene.
    "target_hands": (8, 16), "early_hands": (2, 10), "hands_ramp_day": (2, 12),
}
INTS = set(SEARCH)  # every gene in this space is integer-valued


# measured mean unit prices from the replay corpus -- the imitation must contest each SINK
# in proportion to the DOLLARS the real agent takes out of it, not the unit count.
UNIT_PRICE = {"STRAWBERRY": 205, "MELON": 249, "MILK": 150, "WOOL": 204,
              "FERTILIZER": 61, "WHEAT": 44, "CARROT": 35}


def obj(agg, tgt):
    """Revenue-weighted relative error. Money fidelity is a secondary term."""
    num = den = 0.0
    for k in KEYS:
        t = tgt["sells"].get(k, 0)
        if t < 50:
            continue
        w = t * UNIT_PRICE.get(k, 50)          # dollars the real agent takes from this sink
        num += w * min(2.0, abs(agg["sells"][k] - t) / t)
        den += w
    prod = num / max(1e-9, den)
    mon = min(1.0, abs(agg["money"] - tgt["money"]) / tgt["money"])
    return 0.72 * prod + 0.28 * mon


def _eval_one(args):
    genome, seeds = args
    from fit import evaluate
    try:
        return evaluate(genome, seeds=seeds, workers=1)
    except Exception as e:
        return {"err": f"{type(e).__name__}: {e}"}


def cem(name, pinned, gens=6, pop=24, elite=6, seeds=(60000, 60001), workers=14, init=None):
    tgt = TARGETS[name]
    rng = random.Random(7)
    mu = {}
    sd = {}
    for g, (lo, hi) in SEARCH.items():
        mu[g] = float(init[g]) if init and g in init else (lo + hi) / 2.0
        sd[g] = (hi - lo) / 4.0
    best = (1e9, None, None)
    for it in range(gens):
        cands = []
        for _ in range(pop):
            gm = dict(pinned)
            for g, (lo, hi) in SEARCH.items():
                v = rng.gauss(mu[g], max(1e-6, sd[g]))
                v = max(lo, min(hi, v))
                gm[g] = int(round(v))
            cands.append(gm)
        if it == 0 and init:
            # seed candidate 0 with `init`, but fill any gene `init` does not carry from the
            # current mean -- otherwise the elite update KeyErrors on a newly added gene.
            gm = dict(cands[0])
            gm.update({k: int(init[k]) for k in SEARCH if k in init})
            cands[0] = gm
        with ProcessPoolExecutor(max_workers=workers) as ex:
            aggs = list(ex.map(_eval_one, [(c, seeds) for c in cands]))
        scored = []
        for c, a in zip(cands, aggs):
            if "err" in a or a.get("crashed"):
                continue
            scored.append((obj(a, tgt), c, a))
        if not scored:
            print(f"  gen{it}: all failed"); continue
        scored.sort(key=lambda t: t[0])
        if scored[0][0] < best[0]:
            best = scored[0]
        el = scored[:elite]
        for g in SEARCH:
            vals = [c[g] for _, c, _ in el]
            mu[g] = st.mean(vals)
            lo, hi = SEARCH[g]
            sd[g] = max((hi - lo) / 40.0, st.pstdev(vals) if len(vals) > 1 else sd[g] * 0.7)
        a = scored[0][2]
        print(f"  gen{it}: best obj {scored[0][0]:.4f}  money ${a['money']:>8,.0f}  "
              + " ".join(f"{k[:4]}={a['sells'][k]:4.0f}" for k in ("STRAWBERRY", "MELON", "MILK", "WOOL", "FERTILIZER")),
              flush=True)
    return best
