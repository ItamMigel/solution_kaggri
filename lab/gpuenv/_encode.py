"""Conversion between the real interpreter's Python state / actions and the
batched tensors.  Used by the local differential tests (and available to WP1).

``ref_snapshot`` and ``gpu_snapshot`` return the *same* canonical dict of numpy
arrays, so a full-state comparison is ``np.array_equal`` per key.
"""

from __future__ import annotations

import numpy as np
import torch

from . import ops as O
from . import _consts as C
from . import _prices as P
from ._state import Actions

_TILE_FIELDS = ("kind", "species", "tday", "tyield", "tflag", "tcons", "tmls",
                "tfert", "tcared", "tfavail", "tcare")
_N_TF = len(_TILE_FIELDS)


# --------------------------------------------------------------------------- #
# actions
# --------------------------------------------------------------------------- #
def encode_actions(action_pairs, max_hands=O.MAX_HANDS, max_orders=O.MAX_ORDERS,
                   device="cpu") -> Actions:
    """``action_pairs``: list (len B) of 2-element lists of action dicts."""
    b = len(action_pairs)
    farmer = np.zeros((b, 2, 3), dtype=np.int32)
    hands = np.zeros((b, 2, max_hands, 3), dtype=np.int32)
    market = np.zeros((b, 2, max_orders, 3), dtype=np.int32)
    for i, pair in enumerate(action_pairs):
        for p in range(2):
            a = pair[p] if isinstance(pair[p], dict) else {}
            farmer[i, p] = O.encode_unit_action(a.get("farmer", ["PASS"]))
            hs = a.get("hands", [])
            if not isinstance(hs, list):
                hs = []
            for j, h in enumerate(hs[:max_hands]):
                hands[i, p, j] = O.encode_unit_action(h)
            ms = a.get("market", [])
            if not isinstance(ms, list):
                ms = []
            for j, m in enumerate(ms[:max_orders]):
                market[i, p, j] = O.encode_market_order(m)
    dev = torch.device(device)
    return Actions(torch.from_numpy(farmer).to(dev),
                   torch.from_numpy(hands).to(dev),
                   torch.from_numpy(market).to(dev))


# --------------------------------------------------------------------------- #
# reference -> canonical snapshot
# --------------------------------------------------------------------------- #
def _canon_tile(tile):
    out = [0] * _N_TF
    if tile is None:
        out[0] = O.TILE_EMPTY
        return out
    if tile == "LOCKED":
        out[0] = O.TILE_LOCKED
        return out
    kind = tile.get("kind")
    if "animal" in tile:
        out[0] = O.TILE_ANIMAL
        out[1] = O.ITEM_ID[tile["animal"]] - O.ITEM_GOOSE
        out[2] = tile["placed_day"]
        out[3] = tile["yield_units"]
        out[4] = int(tile["fed_today"])
        out[5] = tile["consecutive_unfed"]
        out[8] = int(tile["cared_today"])
        out[9] = int(tile["fertilizer_available"])
        out[10] = tile.get("pending_care_bonus", 0)
        return out
    if kind == "PLANT":
        out[0] = O.TILE_PLANT
        out[1] = O.ITEM_ID[tile["crop"]]
        out[2] = tile["planted_day"]
        out[3] = tile["yield_units"]
        out[4] = int(tile["watered_today"])
        out[5] = tile["consecutive_unwatered"]
        out[6] = tile["max_lifespan_step"]
        out[7] = tile.get("fertilized_until_day", -1)
        return out
    out[0] = {"WEED": O.TILE_WEED, "COOP": O.TILE_COOP,
              "PASTURE": O.TILE_PASTURE}.get(kind, O.TILE_EMPTY)
    return out


def ref_snapshot(state, max_units=O.MAX_HANDS + 1) -> dict:
    obs0 = state[0].observation
    farms = obs0["farms"]
    market = obs0["market"]
    town = obs0["town"]
    privates = [state[p].observation["private"] for p in range(2)]

    tiles = np.zeros((2, C.N_TILES, _N_TF), dtype=np.int64)
    for p in range(2):
        rows = farms[p]["tiles"]
        for y in range(C.BOARD_SIZE):
            for x in range(C.BOARD_SIZE):
                tiles[p, y * C.BOARD_SIZE + x] = _canon_tile(rows[y][x])

    shed = np.zeros((2, O.N_ITEMS), dtype=np.int64)
    seeds = np.zeros((2, O.N_CROPS), dtype=np.int64)
    inv = np.zeros((2, max_units, O.N_ITEMS), dtype=np.int64)
    ux = np.full((2, max_units), C.HALF - 1, dtype=np.int64)
    uy = np.full((2, max_units), C.HALF - 1, dtype=np.int64)
    for p in range(2):
        for name, n in privates[p]["shed"].items():
            shed[p, O.ITEM_ID[name]] = n
        for name, n in privates[p]["seeds"].items():
            seeds[p, O.ITEM_ID[name]] = n
        for u, d in enumerate(privates[p]["inventories"][:max_units]):
            for name, n in d.items():
                inv[p, u, O.ITEM_ID[name]] = n
        ux[p, 0], uy[p, 0] = farms[p]["farmer"]
        for h, pos in enumerate(farms[p]["hands"][:max_units - 1]):
            ux[p, h + 1], uy[p, h + 1] = pos

    shops = np.zeros(C.N_SHOPS, dtype=np.int64)
    for s in town["unlocked_shops"]:
        shops[C.SHOP_NAMES.index(s)] = 1

    return {
        "money": np.array([farms[p]["money"] for p in range(2)], dtype=np.int64),
        "tiles": tiles,
        "shed": shed,
        "seeds": seeds,
        "inv": inv,
        "ux": ux,
        "uy": uy,
        "n_hands": np.array([len(farms[p]["hands"]) for p in range(2)], dtype=np.int64),
        "hires_today": np.array([farms[p]["hires_today"] for p in range(2)], dtype=np.int64),
        "land": np.array([len(farms[p]["unlocked_quadrants"]) - 1 for p in range(2)],
                         dtype=np.int64),
        "market_inv": np.array([market["inventory"][n] for n in O.PRODUCT_NAMES],
                               dtype=np.int64),
        "prices": np.array([market["prices"][n] for n in O.PRODUCT_NAMES], dtype=np.int64),
        "shops": shops,
    }


# --------------------------------------------------------------------------- #
# batched state -> canonical snapshot
# --------------------------------------------------------------------------- #
def gpu_snapshot(st, b: int) -> dict:
    tiles = np.stack([getattr(st, f)[b].to(torch.int64).cpu().numpy()
                      for f in _TILE_FIELDS], axis=-1)
    inv = st.inv[b].to(torch.int64).cpu().numpy()
    n_hands = st.n_hands[b].to(torch.int64).cpu().numpy()
    # units past n_hands do not exist in the reference; blank them so the
    # comparison is apples to apples.
    ux = st.ux[b].to(torch.int64).cpu().numpy()
    uy = st.uy[b].to(torch.int64).cpu().numpy()
    for p in range(2):
        ux[p, n_hands[p] + 1:] = C.HALF - 1
        uy[p, n_hands[p] + 1:] = C.HALF - 1
        inv[p, n_hands[p] + 1:] = 0
    mkt = st.market_inv[b].cpu().numpy()
    # exercise the tensor price table (State.market_price), not the Python helper
    prices = st.market_price()[b].cpu().numpy().astype(np.int64)
    return {
        "money": st.money[b].cpu().numpy().astype(np.int64),
        "tiles": tiles,
        "shed": st.shed[b].cpu().numpy().astype(np.int64),
        "seeds": st.seeds[b].cpu().numpy().astype(np.int64),
        "inv": inv,
        "ux": ux,
        "uy": uy,
        "n_hands": n_hands,
        "hires_today": st.hires_today[b].to(torch.int64).cpu().numpy(),
        "land": st.land[b].to(torch.int64).cpu().numpy(),
        "market_inv": mkt.astype(np.int64),
        "prices": prices,
        "shops": st.shops[b].to(torch.int64).cpu().numpy(),
    }


def diff_snapshots(ref: dict, got: dict):
    """Returns a list of (key, detail) for every field that differs."""
    out = []
    for k in ref:
        a, c = ref[k], got[k]
        if np.array_equal(a, c):
            continue
        if k == "tiles":
            bad = np.argwhere(a != c)
            first = bad[0]
            out.append((k, f"{len(bad)} cells differ; first player={first[0]} "
                            f"tile=({first[1] // 10},{first[1] % 10}) "
                            f"field={_TILE_FIELDS[first[2]]} "
                            f"ref={a[tuple(first)]} got={c[tuple(first)]}"))
        else:
            out.append((k, f"ref={a.tolist()} got={c.tolist()}"))
    return out
