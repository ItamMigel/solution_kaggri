"""BC v3 features + lossless action codec (verified: codec round-trip reproduces 102/102 Boey games exactly,
see lab/pavel/codec_ceiling.py variant v3).

Differences vs lab/bc/feat.py (v2):
- board: own farm (30 ch, v2 board_tensor) + opponent farm (27 ch: v2 channels 0..25 and 29)
- glob: v2 glob_vec + hour one-hot (24) + market/money history deltas for lags 1..3 (3 x 20)
- unit vec: v2 unit vec + unit index one-hot (17: farmer + 16 hands)
- unit labels: op class (v2 vocabulary) + quantity class for PICKUP/PLACE (QTY_VALS)
- market labels: ordered slot sequence of up to 10 tokens incl. NOOP, END terminator, quantity class 1..QMAX
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bc"))
import feat  # noqa: E402  (lab/bc/feat.py)

N = feat.N; CROPS = feat.CROPS; PRODUCTS = feat.PRODUCTS; ANIMALS = feat.ANIMALS; ITEMS = feat.ITEMS
UNIT_OPS = feat.UNIT_OPS; UNIT_IDX = feat.UNIT_IDX
MAX_UNITS = 17
LAGS = 3
OPP_CH = list(range(26)) + [29]
C_BOARD = feat.C_BOARD + len(OPP_CH)
HIST_DIM = 9 + 9 + 2
G_DIM = feat.G_DIM + 24 + LAGS * HIST_DIM
U_DIM = feat.U_DIM + MAX_UNITS

QTY_VALS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 99]
QTY_ARR = np.array(QTY_VALS)

TOKENS = (["END", "NOOP", "HIRE", "BUY_LAND"] + ["SELL:" + p for p in PRODUCTS]
          + ["BUY_PRODUCT:WHEAT", "BUY_PRODUCT:FERTILIZER"] + ["BUY_SEED:" + c for c in CROPS]
          + ["BUY_ANIMAL:" + a for a in ANIMALS])
TOK_IDX = {k: i for i, k in enumerate(TOKENS)}
N_TOK = len(TOKENS)
QMAX = 40
N_SLOTS = 10
IGNORE = -100


def _g(d, k, default=None):
    try:
        v = d.get(k, default)
    except AttributeError:
        v = getattr(d, k, default)
    return default if v is None else v


# ------------------------------------------------------------------ history
def snapshot(obs, p):
    m = _g(obs, "market", {}) or {}; inv = _g(m, "inventory", {}) or {}; pr = _g(m, "prices", {}) or {}
    farms = _g(obs, "farms")
    return np.array([float(inv.get(i, 10000)) for i in PRODUCTS] + [float(pr.get(i, 0)) for i in PRODUCTS]
                    + [float(farms[p]["money"]), float(farms[1 - p]["money"])], np.float64)


_HSCALE = np.array([20.0] * 9 + [feat.BASE_PRICE[i] * 0.1 for i in PRODUCTS] + [1000.0, 1000.0])


def hist_features(snaps):
    """snaps: list of snapshots, snaps[-1] = current step, earlier = previous steps (may be shorter than LAGS+1)."""
    cur = snaps[-1]; out = []
    for lag in range(1, LAGS + 1):
        prev = snaps[-1 - lag] if len(snaps) > lag else snaps[0]
        out.append(np.clip((cur - prev) / _HSCALE, -10, 10))
    return np.concatenate(out).astype(np.float32)


# ------------------------------------------------------------------ observation features
def board3(obs, p):
    own = feat.board_tensor(obs, p); opp = feat.board_tensor(obs, 1 - p)[OPP_CH]
    return np.concatenate([own, opp], 0)


def glob3(obs, p, hist):
    hour = int(_g(obs, "hour", int(_g(obs, "step", 0)) % 24))
    oh = np.zeros(24, np.float32); oh[hour % 24] = 1
    return np.concatenate([feat.glob_vec(obs, p), oh, hist]).astype(np.float32)


def units3(obs, p):
    out = []
    for i, (x, y, v) in enumerate(feat.unit_list(obs, p)):
        oh = np.zeros(MAX_UNITS, np.float32); oh[min(i, MAX_UNITS - 1)] = 1
        out.append((x, y, np.concatenate([v, oh])))
    return out


# ------------------------------------------------------------------ unit codec
def qty_class(n):
    return int(np.abs(QTY_ARR - int(n)).argmin())


def encode_unit(a):
    """-> (op class, qty class or IGNORE)"""
    cls = feat.encode_unit_action(a)
    k = UNIT_OPS[cls]
    if (k.startswith("PICKUP:") or k.startswith("PLACE:")) and a and len(a) > 2:
        return cls, qty_class(a[2])
    return cls, IGNORE


def decode_unit(cls, qcls=None):
    k = UNIT_OPS[int(cls)]
    if ":" not in k:
        return [k]
    op, it = k.split(":")
    if op == "PLANT":
        return ["PLANT", it]
    return [op, it, QTY_VALS[int(qcls)] if qcls is not None else 1]


# ------------------------------------------------------------------ market codec
def _order_token(o):
    if not isinstance(o, list) or not o:
        return "NOOP", None
    if o[0] in ("HIRE", "BUY_LAND"):
        return o[0], None
    if o[0] in ("SELL", "BUY_PRODUCT", "BUY_SEED", "BUY_ANIMAL") and len(o) > 2:
        try:
            n = int(o[2])
        except (TypeError, ValueError):
            return "NOOP", None
        key = o[0] + ":" + str(o[1])
        if n <= 0 or key not in TOK_IDX:
            return "NOOP", None
        return key, max(1, min(n, QMAX))
    return "NOOP", None


def encode_market_seq(orders):
    """-> tok[N_SLOTS], qty[N_SLOTS] (qty class = n-1; IGNORE where no qty / after END)"""
    tok = np.full(N_SLOTS, IGNORE, np.int16); qty = np.full(N_SLOTS, IGNORE, np.int16)
    orders = list(orders or [])[:N_SLOTS]
    for s, o in enumerate(orders):
        k, n = _order_token(o); tok[s] = TOK_IDX[k]
        if n is not None:
            qty[s] = n - 1
    if len(orders) < N_SLOTS:
        tok[len(orders)] = TOK_IDX["END"]
    return tok, qty


def decode_market_seq(toks, qtys):
    out = []
    for t, q in zip(toks, qtys):
        k = TOKENS[int(t)]
        if k == "END":
            break
        if k in ("NOOP", "HIRE", "BUY_LAND"):
            out.append([k])
        else:
            op, it = k.split(":"); out.append([op, it, int(q) + 1])
    return out[:N_SLOTS]


MS_DIM = len(ITEMS)
SHED_ADJ = {(4, 4), (5, 4), (4, 5), (5, 5)}
_STRUCT = {"GOOSE": "COOP", "COW": "PASTURE", "SHEEP": "PASTURE"}


def shed_after_units(obs, p, unit_actions, capacity=100):
    """Shed contents at market time: unit actions resolve before the market in the engine
    (DROP moves the whole unit inventory, PLACE at a shed-access tile moves n, PICKUP takes n from the shed).
    Mirrors kaggriculture._apply_unit_action for these three ops, farmer first then hands in order."""
    priv = _g(obs, "private", {}) or {}
    shed = {it: int((_g(priv, "shed", {}) or {}).get(it, 0)) for it in ITEMS}
    invs = [dict(i or {}) for i in (_g(priv, "inventories", []) or [])]
    farm = _g(obs, "farms")[p]
    pos = [farm["farmer"]] + list(farm.get("hands") or [])
    for i, a in enumerate(unit_actions or []):
        if not a or i >= len(pos) or i >= len(invs):
            continue
        op = a[0]; x, y = pos[i]; adj = (int(x), int(y)) in SHED_ADJ; inv = invs[i]
        if op == "DROP" and adj:
            for it, n in inv.items():
                room = max(0, capacity - sum(shed.values())); take = min(int(n), room)
                if it in shed and take > 0:
                    shed[it] += take
        elif op == "PICKUP" and adj and len(a) > 1 and a[1] in shed:
            n = int(a[2]) if len(a) > 2 else 1; n = min(max(n, 0), shed[a[1]]); shed[a[1]] -= n
        elif op == "PLACE" and len(a) > 1 and a[1] in shed:
            t = farm["tiles"][int(y)][int(x)]
            if a[1] in _STRUCT and isinstance(t, dict) and t.get("kind") == _STRUCT[a[1]] and t.get("animal") is None:
                continue
            if adj:
                n = int(a[2]) if len(a) > 2 else 1; n = min(max(n, 0), int(inv.get(a[1], 0)))
                n = min(n, max(0, capacity - sum(shed.values()))); shed[a[1]] += n
    return np.array([shed[it] for it in ITEMS], np.float32) / 50.0


def merged_obs(d, t, p):
    """Replay observation of player p at step t with shared fields filled in (replays store them only for p0)."""
    import copy
    o = copy.deepcopy(d["steps"][t][p]["observation"]); sh = d["steps"][t][0]["observation"]
    for k in ("step", "day", "hour", "farms", "market", "town"):
        if k not in o and k in sh:
            o[k] = copy.deepcopy(sh[k])
    o["player"] = p
    if "step" not in o:
        o["step"] = t
    return o
