"""WP1 — differential test harness for the batched kaggriculture env (the fidelity gate).

Replays the recorded action sequences in `artifacts/vectors/` through any implementation of the
CONTRACT env API and compares the FULL canonical state at EVERY step against the real
simulator's recorded trajectory.

    python -m src.gpuenv.difftest --impl src.gpuenv.env:VecKaggriculture
    python -m src.gpuenv.difftest --self-test            # ground truth vs itself (harness sanity)

Exit code 0 iff zero divergences.

What the implementation must provide
------------------------------------
1. `Impl(n_envs, device=..., dtype=...)`, `reset(seeds)->State`,
   `step(state, actions)->(state, reward, done, info)`   (CONTRACT.md).
2. A canonical view of the state, so the two worlds can be compared:
       `impl.canonical(state) -> dict[str, Tensor]`      (preferred; `to_canonical` also accepted)
   with exactly the keys / shapes / dtypes of spec.md §14.  If neither method exists the harness
   falls back to reading attributes of `State` with those names, and if that fails it aborts with
   an explicit message.  Without this there is no fidelity gate.
3. Action tensors laid out `[B, 2, ...]` (batch, player, ...).  An implementation that wants
   `[2, B, ...]` may set the class attribute `ACTION_PLAYER_AXIS = 0`.

Reporting
---------
* the FIRST divergence per env: (episode, env index, step, field, cell index, expected, actual);
* an explicit split between "money differs" and "money matches but state differs" — the latter is
  reported as loudly as the former, because a wrong intermediate state that happens to end on the
  same number will diverge under a different policy;
* a per-mechanic breakdown (market / crops / animals / logistics / movement / town / time) so the
  failing subsystem is identifiable without bisecting by hand.
"""
from __future__ import annotations

import argparse
import glob
import importlib
import json
import os
import sys
import time

import numpy as np

from src.gpuenv.record_vectors import (
    CANON_DTYPE, CANON_KEYS, CANON_SHAPE, ITEMS, MAX_HANDS, MAX_ORDERS, MAX_UNITS, PRODUCTS,
    CROPS, SHOPS, STEPS, OPS_FINGERPRINT, OPS_SOURCE, K_ANIMAL, K_COOP, K_PASTURE, K_PLANT,
    decode_actions, extract_state, MARKET_OP_ID, UNIT_OP_ID, VEC_DIR,
)

# --------------------------------------------------------------------------------------
# Mechanic map: which canonical field (and which slice of it) belongs to which subsystem
# --------------------------------------------------------------------------------------

TILE_FIELD_NAMES = ["kind", "crop", "animal", "day0", "flag_wf", "cu", "yield_units",
                    "mls", "fert_until", "cared", "fert_avail", "care_bank"]

MECHANIC_OF_FIELD = {
    "money": "economy/market",
    "mkt_inv": "market+town",
    "mkt_price": "market pricing",
    "shops": "town/RNG(shop unlock)",
    "shed": "logistics(shed)",
    "seeds": "logistics(seeds)",
    "inv": "logistics(unit inventories)",
    "farmer": "movement(farmer)",
    "hands": "movement/hiring(hands)",
    "n_hands": "hiring",
    "hires_today": "hiring",
    "n_land": "economy(land)",
    "day": "time",
    "hour": "time",
    "step": "time",
}
MECHANIC_OF_TILE_FIELD = {
    "kind": "tiles(kind: plant/weed/structure)",
    "crop": "tiles(crop identity)",
    "animal": "animals(placement/escape)",
    "day0": "tiles(planted/placed day)",
    "flag_wf": "crops(watered)/animals(fed)",
    "cu": "crops(dry death)/animals(starvation)",
    "yield_units": "yield(growth/production/harvest/decay)",
    "mls": "crops(lifespan/decay schedule)",
    "fert_until": "crops(FERTILIZE)",
    "cared": "animals(CARE flag)",
    "fert_avail": "animals(COLLECT_FERTILIZER)",
    "care_bank": "animals(pending_care_bonus)",
}


def _to_numpy(x):
    if isinstance(x, np.ndarray):
        return x
    if hasattr(x, "detach"):
        return x.detach().cpu().numpy()
    return np.asarray(x)


# --------------------------------------------------------------------------------------
# Convention normalisation + comparison masks
#
# Two implementations can be BIT-IDENTICAL in game semantics and still disagree on values
# that carry no meaning (the crop id of an empty tile, the inventory of a hand that has not
# been hired).  Comparing those produces false failures and hides real ones.  So:
#   * normalise the two known encodings of an occupied structure and of the animal id;
#   * compare each tile field only where it is MEANINGFUL, and each unit slot only where
#     the unit exists.
# Nothing that carries meaning is excluded: a field becomes live on exactly the step its
# tile/unit comes into existence, and is compared from that step on.
# --------------------------------------------------------------------------------------

def normalize_canon(c: dict) -> dict:
    """Accept either tile-kind convention and either animal-id space."""
    c = dict(c)
    t = np.array(c["tiles"], copy=True)
    kind, animal = t[..., 0], t[..., 2]
    animal = np.where(animal >= 9, animal - 9, animal)          # item-id space -> 0..2
    t[..., 2] = animal
    occupied = (animal >= 0) & np.isin(kind, (K_COOP, K_PASTURE, K_ANIMAL))
    t[..., 0] = np.where(occupied, K_ANIMAL, kind)              # empty structure keeps 4/5
    c["tiles"] = t
    return c


def comparison_masks(exp: dict):
    """Boolean masks (broadcastable to each field) marking the cells that carry meaning."""
    kind = exp["tiles"][..., 0]                                  # [B,2,10,10]
    is_plant = kind == K_PLANT
    is_animal = kind == K_ANIMAL
    tile_mask = np.ones(exp["tiles"].shape, bool)
    for f in (1, 7, 8):                       # crop, max_lifespan_step, fertilized_until_day
        tile_mask[..., f] = is_plant
    for f in (2, 9, 10, 11):                  # animal, cared, fert_avail, care_bank
        tile_mask[..., f] = is_animal
    for f in (3, 4, 5, 6):                    # day0, watered/fed, cu, yield_units
        tile_mask[..., f] = is_plant | is_animal

    n_hands = exp["n_hands"]                                     # [B,2]
    slot = np.arange(MAX_HANDS)[None, None, :]
    hand_live = slot < n_hands[..., None]                        # [B,2,MAX_HANDS]
    unit_live = np.arange(MAX_UNITS)[None, None, :] <= n_hands[..., None]
    return {
        "tiles": tile_mask,
        "hands": np.repeat(hand_live[..., None], 2, axis=-1),
        "inv": np.repeat(unit_live[..., None], len(ITEMS), axis=-1),
    }


# --------------------------------------------------------------------------------------
# Ground-truth adapter: the REAL simulator wrapped in the contract API
# --------------------------------------------------------------------------------------

class RealSimAdapter:
    """The real kaggriculture simulator behind the CONTRACT env API.

    Exists purely so the harness can be validated against ground truth (`--self-test`).
    It is a Python loop over `n_envs` independent `kaggle_environments` episodes; it is slow
    and that is fine.
    """

    ACTION_PLAYER_AXIS = 1

    def __init__(self, n_envs: int, device: str = "cpu", dtype=None):
        self.n_envs = n_envs

    def reset(self, seeds):
        from kaggle_environments import make
        seeds = [int(s) for s in _to_numpy(seeds).reshape(-1)]
        assert len(seeds) == self.n_envs
        self.envs = [make("kaggriculture",
                          configuration={"episodeSteps": STEPS, "seed": s}, debug=False)
                     for s in seeds]
        return self.envs

    def step(self, state, actions):
        af = _to_numpy(actions.farmer)
        ah = _to_numpy(actions.hands)
        am = _to_numpy(actions.market)
        rewards = np.zeros(self.n_envs, np.float32)
        done = np.zeros(self.n_envs, bool)
        for b, env in enumerate(state):
            acts = decode_actions(af[b], ah[b], am[b])
            env.step(acts)
            if env.done:
                done[b] = True
                r0, r1 = env.steps[-1][0].get("reward"), env.steps[-1][1].get("reward")
                rewards[b] = float(r0) - float(r1)
        return state, rewards, done, {}

    def canonical(self, state):
        out = {k: np.zeros((self.n_envs,) + CANON_SHAPE[k], CANON_DTYPE[k]) for k in CANON_KEYS}
        for b, env in enumerate(state):
            st = extract_state(env.steps[-1])
            for k in CANON_KEYS:
                out[k][b] = st[k]
        return out


# --------------------------------------------------------------------------------------
# Impl loading / adaptation
# --------------------------------------------------------------------------------------

class _Actions:
    """Minimal action container; supports attribute and item access."""

    __slots__ = ("farmer", "hands", "market")

    def __init__(self, farmer, hands, market):
        self.farmer, self.hands, self.market = farmer, hands, market

    def __getitem__(self, k):
        return getattr(self, k)

    def keys(self):
        return ("farmer", "hands", "market")


def load_impl(spec: str):
    if spec in ("self", "self-test", "real"):
        return RealSimAdapter, None
    if ":" not in spec:
        raise SystemExit(f"--impl must be 'module:ClassName', got {spec!r}")
    modname, clsname = spec.split(":", 1)
    mod = importlib.import_module(modname)
    cls = getattr(mod, clsname, None)
    if cls is None:
        raise SystemExit(f"{modname} has no attribute {clsname!r}")
    return cls, mod


def check_ops_agreement(episodes):
    """The corpus stores the op-id fingerprint it was encoded with; it must equal the one in
    force now (i.e. `src/gpuenv/ops.py`).  Otherwise the replayed actions mean something else.
    """
    problems = []
    stale = [e for e in episodes if e.ops_fp is not None and e.ops_fp != OPS_FINGERPRINT]
    if stale:
        problems.append(
            f"{len(stale)}/{len(episodes)} vector files were recorded with DIFFERENT op ids "
            f"than {OPS_SOURCE} defines now — re-record: "
            f"`python -m src.gpuenv.record_vectors`")
    legacy = [e for e in episodes if e.ops_fp is None]
    if legacy:
        problems.append(f"{len(legacy)} vector files carry no op fingerprint (pre-dating the "
                        f"check); re-record them to be safe")
    return problems


_PRICE_WARNED = [False]

# spec §5.4 — reference price curve, used only by the auto-adapter fallback
_MKT = {
    "WHEAT": (25, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT": (35, 450, "log", 0.20, "sqrt", 0.70),
    "TOMATO": (60, 200, "linear", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON": (250, 300, "log", 0.20, "sq", 3.60),
    "EGG": (50, 332, "linear", 0.40, "log", 0.20),
    "MILK": (160, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL": (200, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40),
}


def _shape(f, x):
    x = np.maximum(0.0, np.asarray(x, np.float64))
    return {"linear": x, "sq": x * x, "sqrt": np.sqrt(x),
            "log": np.log1p(x), "log10": np.log10(1.0 + x)}[f]


def reference_prices(mkt_inv):
    """[B,9] inventories -> [B,9] int prices (round-half-to-even, floor 1)."""
    out = np.zeros(mkt_inv.shape, np.int64)
    for i, name in enumerate(PRODUCTS):
        base, T, bf, bt, af, at = _MKT[name]
        inv = np.asarray(mkt_inv[:, i], np.float64)
        below = base + (bt * base / _shape(bf, T)) * _shape(bf, 10000 - inv)
        above = base - (at * base / _shape(af, T)) * _shape(af, inv - 10000)
        price = np.where(inv < 10000, below, above)
        out[:, i] = np.maximum(1, np.rint(price).astype(np.int64))
    return out


def auto_canonical(state):
    """Best-effort adapter for a State that carries the game's fields under other names.

    Recognises the WP2 layout (`kind/species/tday/.../ux/uy/market_inv`) documented in
    `src/gpuenv/_state.py`.  Returns None if the layout is not recognised.
    """
    need = ("money", "kind", "species", "tday", "tyield", "tflag", "tcons", "tmls", "tfert",
            "tcared", "tfavail", "tcare", "ux", "uy", "n_hands", "hires_today", "shed",
            "seeds", "inv", "market_inv", "shops")
    if not all(hasattr(state, a) for a in need):
        return None
    g = lambda a: _to_numpy(getattr(state, a))
    B = g("money").shape[0]
    kind = g("kind").reshape(B, 2, 10, 10)
    species = g("species").reshape(B, 2, 10, 10)
    from src.gpuenv.record_vectors import K_PLANT as KP, K_ANIMAL as KA
    tiles = np.zeros((B, 2, 10, 10, 12), np.int64)
    tiles[..., 0] = kind
    tiles[..., 1] = np.where(kind == KP, species, -1)
    tiles[..., 2] = np.where(kind == KA, species, -1)
    for f, a in ((3, "tday"), (4, "tflag"), (5, "tcons"), (6, "tyield"),
                 (7, "tmls"), (8, "tfert"), (9, "tcared"), (10, "tfavail"), (11, "tcare")):
        tiles[..., f] = g(a).reshape(B, 2, 10, 10).astype(np.int64)
    ux, uy = g("ux"), g("uy")
    n_hands = g("n_hands").astype(np.int64)
    hands = np.stack([ux[:, :, 1:1 + MAX_HANDS], uy[:, :, 1:1 + MAX_HANDS]], axis=-1)
    shops_bool = g("shops")                          # [B,8] in ALPHABETICAL shop order
    alpha = sorted(SHOPS)
    perm = [SHOPS.index(s) for s in alpha]
    bits = np.zeros(B, np.int64)
    for j, src_idx in enumerate(perm):
        bits |= (shops_bool[:, j].astype(np.int64) << src_idx)
    step = np.asarray(_to_numpy(getattr(state, "step"))).reshape(-1)
    step = np.broadcast_to(step, (B,)).astype(np.int64) if step.size in (1, B) else step
    land = g("land") if hasattr(state, "land") else np.zeros((B, 2), np.int64)
    mkt_inv = g("market_inv").astype(np.int64)
    if hasattr(state, "market_price"):
        prices = _to_numpy(state.market_price).astype(np.int64)
    else:
        if not _PRICE_WARNED[0]:
            print("[adapter] State carries no `market_price`; prices are DERIVED from "
                  "market_inv with WP1's reference curve, so the impl's own price function "
                  "is NOT under test. Implement `canonical()` to close that hole.")
            _PRICE_WARNED[0] = True
        prices = reference_prices(mkt_inv)
    return {
        "money": g("money").astype(np.int64),
        "farmer": np.stack([ux[:, :, 0], uy[:, :, 0]], axis=-1).astype(np.int64),
        "n_hands": n_hands,
        "hands": hands.astype(np.int64),
        "hires_today": g("hires_today").astype(np.int64),
        "n_land": land.astype(np.int64),
        "shed": g("shed").astype(np.int64),
        "seeds": g("seeds").astype(np.int64),
        "inv": g("inv")[:, :, :MAX_UNITS].astype(np.int64),
        "tiles": tiles,
        "mkt_inv": mkt_inv,
        "mkt_price": prices,
        "shops": bits,
        "day": step // 24,
        "hour": step % 24,
        "step": step,
    }


def get_canonical(impl, state):
    for name in ("canonical", "to_canonical"):
        fn = getattr(impl, name, None)
        if callable(fn):
            return {k: _to_numpy(v) for k, v in fn(state).items()}
    fn = getattr(state, "canonical", None)
    if callable(fn):
        return {k: _to_numpy(v) for k, v in fn().items()}
    if all(hasattr(state, k) for k in CANON_KEYS):
        return {k: _to_numpy(getattr(state, k)) for k in CANON_KEYS}
    auto = auto_canonical(state)
    if auto is not None:
        return auto
    missing = [k for k in CANON_KEYS if not hasattr(state, k)]
    raise SystemExit(
        "FIDELITY GATE CANNOT RUN: the implementation exposes no canonical state view.\n"
        "  Add `def canonical(self, state) -> dict[str, Tensor]` to the env class, returning the\n"
        "  keys/shapes/dtypes of src/gpuenv/spec.md §14.\n"
        f"  (State is also missing these attributes: {missing[:6]}{'...' if len(missing) > 6 else ''})"
    )


# --------------------------------------------------------------------------------------
# Vector loading
# --------------------------------------------------------------------------------------

class Episode:
    __slots__ = ("path", "seed", "agents", "canon", "a_farmer", "a_hands", "a_market", "flags",
                 "ops_fp")

    def __init__(self, path):
        z = np.load(path, allow_pickle=False)
        self.path = path
        self.seed = int(z["seed"])
        self.agents = [str(a) for a in z["agents"]]
        self.ops_fp = str(z["ops_fp"][0]) if "ops_fp" in z.files else None
        self.canon = {k: z[k] for k in CANON_KEYS}
        self.a_farmer = z["a_farmer"]
        self.a_hands = z["a_hands"]
        self.a_market = z["a_market"]
        self.flags = json.loads(str(z["flags"][0]))


def load_episodes(vec_dir, limit=None, only=None):
    paths = sorted(glob.glob(os.path.join(vec_dir, "ep_*.npz")))
    if not paths:
        raise SystemExit(f"no vectors in {vec_dir} — run `python -m src.gpuenv.record_vectors` first")
    if only:
        paths = [p for p in paths if any(o in os.path.basename(p) for o in only)]
    if limit:
        step = max(1, len(paths) // limit)
        paths = paths[::step][:limit]
    return [Episode(p) for p in paths]


# --------------------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------------------

class Divergence:
    def __init__(self, episode, env_idx, step, field, cell, expected, actual, money_matches):
        self.episode, self.env_idx, self.step = episode, env_idx, step
        self.field, self.cell = field, cell
        self.expected, self.actual = expected, actual
        self.money_matches = money_matches

    def describe(self):
        return (f"episode {self.episode} (env {self.env_idx}) step {self.step}: "
                f"field {self.field}{self.cell} expected {self.expected} got {self.actual} "
                f"[money {'MATCHES' if self.money_matches else 'differs'}]")


def _cell_name(field, idx):
    """Human-readable index for a mismatching cell (idx excludes the batch axis)."""
    if field == "tiles":
        p, y, x, f = idx
        return f"[player {p}][y={y}][x={x}][{TILE_FIELD_NAMES[f]}]"
    if field in ("shed", "inv"):
        if field == "shed":
            p, i = idx
            return f"[player {p}][{ITEMS[i]}]"
        p, u, i = idx
        return f"[player {p}][unit {u}][{ITEMS[i]}]"
    if field == "seeds":
        p, c = idx
        return f"[player {p}][{CROPS[c]}]"
    if field in ("mkt_inv", "mkt_price"):
        return f"[{PRODUCTS[idx[0]]}]"
    if field in ("money", "n_hands", "hires_today", "n_land"):
        return f"[player {idx[0]}]"
    if field == "farmer":
        return f"[player {idx[0]}][{'xy'[idx[1]]}]"
    if field == "hands":
        return f"[player {idx[0]}][hand {idx[1]}][{'xy'[idx[2]]}]"
    return "" if not idx else "[" + "][".join(str(i) for i in idx) + "]"


def _mechanic(field, idx):
    if field == "tiles":
        return MECHANIC_OF_TILE_FIELD[TILE_FIELD_NAMES[idx[-1]]]
    return MECHANIC_OF_FIELD.get(field, field)


class Report:
    def __init__(self):
        self.first = None                     # first divergence overall (by step, then episode)
        self.per_env_first = {}               # (episode) -> Divergence
        self.mechanic_hits = {}
        self.field_hits = {}
        self.n_envs_checked = 0
        self.n_steps_compared = 0
        self.money_only = 0
        self.state_only = 0
        self.both = 0
        self.reward_mismatch = []

    def add(self, div: Divergence):
        key = div.episode
        if key in self.per_env_first:
            return
        self.per_env_first[key] = div
        if self.first is None or (div.step, div.episode) < (self.first.step, self.first.episode):
            self.first = div
        m = _mechanic(div.field, div.cell if isinstance(div.cell, tuple) else ())
        self.mechanic_hits[m] = self.mechanic_hits.get(m, 0) + 1
        self.field_hits[div.field] = self.field_hits.get(div.field, 0) + 1

    @property
    def ok(self):
        return not self.per_env_first and not self.reward_mismatch


def compare_batch(exp: dict, got: dict, alive: np.ndarray):
    """Returns list of (b, field, idx_tuple, expected, actual) for envs still alive."""
    out = []
    masks = comparison_masks(exp)
    for field in CANON_KEYS:
        e = exp[field]
        g = got.get(field)
        if g is None:
            out.append((-1, field, (), "present", "MISSING from canonical()"))
            continue
        g = np.asarray(g)
        if g.shape != e.shape:
            out.append((-1, field, (), f"shape {e.shape}", f"shape {g.shape}"))
            continue
        diff = (g.astype(np.int64) != e.astype(np.int64))
        if field in masks:
            diff &= masks[field]
        if not diff.any():
            continue
        idxs = np.argwhere(diff)
        for row in idxs:
            b = int(row[0])
            if not alive[b]:
                continue
            idx = tuple(int(v) for v in row[1:])
            out.append((b, field, idx, e[tuple(row)], g[tuple(row)]))
    return out


def find_actions_factory(impl_cls, mod=None):
    """Use the implementation's own `Actions` container when it has one."""
    for m in (mod, sys.modules.get(impl_cls.__module__)):
        if m is None:
            continue
        A = getattr(m, "Actions", None)
        if A is not None and A is not _Actions:
            return A
    return _Actions


def run_check(impl_cls, episodes, device="cpu", batch=16, verbose=True, use_torch=True,
              stop_after_first=False, actions_factory=None):
    make_actions = actions_factory or _Actions
    rep = Report()
    torch = None
    if use_torch:
        try:
            import torch as _t
            torch = _t
        except ImportError:
            torch = None

    player_axis = getattr(impl_cls, "ACTION_PLAYER_AXIS", 1)

    for start in range(0, len(episodes), batch):
        chunk = episodes[start:start + batch]
        B = len(chunk)
        seeds_np = np.array([e.seed for e in chunk], np.int64)
        impl = impl_cls(B, device=device) if device else impl_cls(B)
        seeds = torch.as_tensor(seeds_np, device=device) if torch is not None else seeds_np
        state = impl.reset(seeds)

        alive = np.ones(B, bool)
        names = [os.path.basename(e.path) for e in chunk]

        # step 0: the post-reset state must equal the recorded initial state
        exp0 = {k: np.stack([e.canon[k][0] for e in chunk]) for k in CANON_KEYS}
        got0 = normalize_canon(get_canonical(impl, state))
        for (b, field, idx, ev, gv) in compare_batch(exp0, got0, alive):
            if b < 0:
                raise SystemExit(f"canonical() schema error on field {field!r}: {ev} vs {gv}")
            rep.add(Divergence(names[b], b, 0, field, idx, int(ev), int(gv),
                               money_matches=bool((exp0["money"][b] == got0["money"][b]).all())))
            alive[b] = False
        rep.n_envs_checked += B

        n_actions = chunk[0].a_farmer.shape[0]
        for t in range(n_actions):
            if not alive.any():
                break
            af = np.stack([e.a_farmer[t] for e in chunk])          # [B,2,3]
            ah = np.stack([e.a_hands[t] for e in chunk])           # [B,2,16,3]
            am = np.stack([e.a_market[t] for e in chunk])          # [B,2,10,3]
            if player_axis == 0:
                af, ah, am = af.swapaxes(0, 1), ah.swapaxes(0, 1), am.swapaxes(0, 1)
            if torch is not None and impl_cls is not RealSimAdapter:
                mk = lambda a: torch.as_tensor(np.ascontiguousarray(a), dtype=torch.int16,
                                               device=device)
                acts = make_actions(mk(af), mk(ah), mk(am))
            else:
                acts = make_actions(af, ah, am)

            actions_obj = acts
            state, reward, done, info = impl.step(state, actions_obj)
            got = normalize_canon(get_canonical(impl, state))
            exp = {k: np.stack([e.canon[k][t + 1] for e in chunk]) for k in CANON_KEYS}
            rep.n_steps_compared += int(alive.sum())

            mism = compare_batch(exp, got, alive)
            if mism:
                money_ok = {}
                for (b, field, idx, ev, gv) in mism:
                    if b < 0:
                        raise SystemExit(f"canonical() schema error on {field!r}: {ev} vs {gv}")
                    if b not in money_ok:
                        money_ok[b] = bool((exp["money"][b] == np.asarray(got["money"])[b]).all())
                for (b, field, idx, ev, gv) in mism:
                    if alive[b]:
                        rep.add(Divergence(names[b], b, t + 1, field, idx, int(ev), int(gv),
                                           money_matches=money_ok[b]))
                for b in money_ok:
                    if alive[b]:
                        d = rep.per_env_first[names[b]]
                        fields = {f for (bb, f, _, _, _) in mism if bb == b}
                        if fields == {"money"}:
                            rep.money_only += 1
                        elif "money" in fields:
                            rep.both += 1
                        else:
                            rep.state_only += 1
                        alive[b] = False
                if stop_after_first:
                    return rep

            # terminal-step reward check
            if t == n_actions - 1:
                r = _to_numpy(reward).reshape(-1)
                d = _to_numpy(done).reshape(-1)
                for b in range(B):
                    if not alive[b]:
                        continue
                    want = int(exp["money"][b, 0]) - int(exp["money"][b, 1])
                    if abs(float(r[b]) - want) > 1e-6:
                        rep.reward_mismatch.append((names[b], want, float(r[b])))
                    if not bool(d[b]):
                        rep.reward_mismatch.append((names[b], "done=True", "done=False"))
        if verbose:
            bad = sum(1 for n in names if n in rep.per_env_first)
            print(f"  batch {start//batch}: {B} episodes, {B-bad} clean, {bad} diverged",
                  flush=True)
    return rep


# --------------------------------------------------------------------------------------
# Parallel self-test (the ground-truth adapter is CPU-bound pure Python)
# --------------------------------------------------------------------------------------

def _selftest_worker(args):
    vec_dir, paths, batch = args
    eps = [Episode(p) for p in paths]
    rep = run_check(RealSimAdapter, eps, device=None, batch=batch, verbose=False, use_torch=False)
    return {
        "n_envs": rep.n_envs_checked,
        "n_steps": rep.n_steps_compared,
        "divs": [(d.episode, d.env_idx, d.step, d.field, str(d.cell), int(d.expected),
                  int(d.actual), d.money_matches) for d in rep.per_env_first.values()],
        "reward_mismatch": rep.reward_mismatch,
    }


def run_selftest_parallel(vec_dir, paths, workers, batch):
    import multiprocessing as mp
    chunks = [paths[i::workers] for i in range(workers)]
    chunks = [c for c in chunks if c]
    jobs = [(vec_dir, c, min(batch, len(c))) for c in chunks]
    with mp.get_context("spawn").Pool(len(jobs)) as pool:
        results = pool.map(_selftest_worker, jobs)
    rep = Report()
    for r in results:
        rep.n_envs_checked += r["n_envs"]
        rep.n_steps_compared += r["n_steps"]
        for (epi, b, step, field, cell, ev, gv, mm) in r["divs"]:
            rep.add(Divergence(epi, b, step, field, cell, ev, gv, mm))
        rep.reward_mismatch.extend(r["reward_mismatch"])
    return rep


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def print_report(rep: Report, label: str, elapsed: float):
    print()
    print("=" * 78)
    print(f"FIDELITY GATE — {label}")
    print("=" * 78)
    print(f"episodes checked : {rep.n_envs_checked}")
    print(f"state comparisons: {rep.n_steps_compared} steps x full canonical state")
    print(f"wall time        : {elapsed:.1f}s")
    if rep.ok:
        print("\nRESULT: PASS — zero divergences at every step of every episode.")
        return 0

    print(f"\nRESULT: FAIL — {len(rep.per_env_first)} of {rep.n_envs_checked} episodes diverged.")
    print("\n--- FIRST DIVERGENCE (earliest step) ---")
    d = rep.first
    print(f"  episode        : {d.episode}")
    print(f"  env index      : {d.env_idx}")
    print(f"  step           : {d.step}   (day {d.step//24}, hour {d.step%24})")
    print(f"  field          : {d.field}{_cell_name(d.field, d.cell) if isinstance(d.cell, tuple) else d.cell}")
    print(f"  expected (real): {d.expected}")
    print(f"  actual   (impl): {d.actual}")
    print(f"  mechanic       : {_mechanic(d.field, d.cell if isinstance(d.cell, tuple) else ())}")

    print("\n--- MONEY vs STATE ---")
    print(f"  money differs only                       : {rep.money_only}")
    print(f"  money AND state differ                   : {rep.both}")
    print(f"  *** state differs but MONEY MATCHES ***  : {rep.state_only}")
    if rep.state_only:
        print("  ^ this is NOT a lesser failure. A wrong intermediate state that happens to end on")
        print("    the same number will diverge as soon as the policy changes. Fix it.")

    print("\n--- PER-MECHANIC BREAKDOWN (episodes whose first divergence was here) ---")
    for m, n in sorted(rep.mechanic_hits.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5d}  {m}")

    print("\n--- FIRST DIVERGENCE PER EPISODE (up to 15) ---")
    for d in sorted(rep.per_env_first.values(), key=lambda d: d.step)[:15]:
        cell = _cell_name(d.field, d.cell) if isinstance(d.cell, tuple) else str(d.cell)
        print(f"  {d.episode:>14s} step {d.step:4d}  {d.field}{cell}  "
              f"exp={d.expected} got={d.actual}")

    if rep.reward_mismatch:
        print(f"\n--- REWARD / DONE MISMATCHES ({len(rep.reward_mismatch)}) ---")
        for row in rep.reward_mismatch[:10]:
            print("  ", row)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--impl", default=None, help="module:ClassName implementing the CONTRACT API")
    ap.add_argument("--self-test", action="store_true",
                    help="run the harness against the real simulator wrapped in the contract API")
    ap.add_argument("--vectors", default=VEC_DIR)
    ap.add_argument("--limit", type=int, default=0, help="check only N episodes (0 = all)")
    ap.add_argument("--only", nargs="*", default=None, help="substring filter on vector filenames")
    ap.add_argument("--batch", type=int, default=16, help="envs per batched reset/step")
    ap.add_argument("--device", default=None, help="device for the impl (default: cuda if available)")
    ap.add_argument("--workers", type=int, default=8, help="self-test only: parallel processes")
    ap.add_argument("--stop-after-first", action="store_true")
    args = ap.parse_args(argv)

    if not args.self_test and not args.impl:
        ap.error("give --impl module:Class, or --self-test")

    t0 = time.time()

    if args.self_test:
        paths = sorted(glob.glob(os.path.join(args.vectors, "ep_*.npz")))
        if not paths:
            raise SystemExit(f"no vectors in {args.vectors}")
        if args.only:
            paths = [p for p in paths if any(o in os.path.basename(p) for o in args.only)]
        if args.limit:
            step = max(1, len(paths) // args.limit)
            paths = paths[::step][:args.limit]
        problems = check_ops_agreement([Episode(paths[0]), Episode(paths[-1])])
        for p in problems:
            print(f"[ops] {p}")
        if problems:
            return 2
        print(f"op ids from {OPS_SOURCE}")
        print(f"self-test: replaying {len(paths)} recorded episodes through the REAL simulator "
              f"wrapped in the contract API ({args.workers} workers)", flush=True)
        if args.workers > 1:
            rep = run_selftest_parallel(args.vectors, paths, args.workers, args.batch)
        else:
            rep = run_check(RealSimAdapter, [Episode(p) for p in paths], device=None,
                            batch=args.batch, use_torch=False)
        return print_report(rep, "SELF-TEST (ground truth vs recorded vectors)", time.time() - t0)

    impl_cls, mod = load_impl(args.impl)
    device = args.device
    if device is None:
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    episodes = load_episodes(args.vectors, args.limit, args.only)
    problems = check_ops_agreement(episodes)
    for p in problems:
        print(f"[ops] {p}")
    if problems:
        print("\nABORT: the vector corpus and the current op ids disagree; replaying would "
              "compare the wrong actions.")
        return 2
    print(f"op ids from {OPS_SOURCE}")
    print(f"checking {args.impl} on {len(episodes)} episodes, batch={args.batch}, device={device}",
          flush=True)
    rep = run_check(impl_cls, episodes, device=device, batch=args.batch,
                    stop_after_first=args.stop_after_first,
                    actions_factory=find_actions_factory(impl_cls, mod))
    return print_report(rep, args.impl, time.time() - t0)


if __name__ == "__main__":
    sys.exit(main())
