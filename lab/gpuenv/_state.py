"""Batched state / action containers.

Every field is a torch tensor.  Leading dims are ``[B]`` (batch) and, for
per-player fields, ``[B, 2]``.  Tiles are stored flat: index ``i = y * 10 + x``.

Canonical tile encoding
-----------------------
The source stores a tile as ``None`` / ``"LOCKED"`` / a dict whose keys depend on
the kind.  Here every tile carries the full field set; fields that the
corresponding source dict does not have are **0**:

===============  ====================================================
kind             live fields
===============  ====================================================
EMPTY / LOCKED   -- (everything 0)
WEED             -- (everything 0)
COOP / PASTURE   -- (everything 0)  [an empty structure, no animal]
PLANT            species=crop id, tday=planted_day, tflag=watered_today,
                 tcons=consecutive_unwatered, tyield=yield_units,
                 tmls=max_lifespan_step, tfert=fertilized_until_day
ANIMAL           species=animal idx, tday=placed_day, tyield=yield_units,
                 tcons=consecutive_unfed, tflag=fed_today, tcared=cared_today,
                 tfavail=fertilizer_available, tcare=pending_care_bonus
===============  ====================================================

``_encode.py`` converts a real observation into exactly this form, so the two
are directly comparable.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

import torch


@dataclass
class State:
    # --- clock -------------------------------------------------------------
    step: torch.Tensor          # int64 []      (scalar; all envs share it)
    seed: torch.Tensor          # int64 [B]
    done: torch.Tensor          # bool  [B]

    # --- farms -------------------------------------------------------------
    money: torch.Tensor         # int64 [B, 2]
    kind: torch.Tensor          # int32 [B, 2, 100]
    species: torch.Tensor       # int32 [B, 2, 100]
    tday: torch.Tensor          # int32 [B, 2, 100]  planted_day / placed_day
    tyield: torch.Tensor        # int32 [B, 2, 100]
    tflag: torch.Tensor         # bool  [B, 2, 100]  watered_today / fed_today
    tcons: torch.Tensor         # int32 [B, 2, 100]  consecutive_unwatered/unfed
    tmls: torch.Tensor          # int32 [B, 2, 100]  max_lifespan_step
    tfert: torch.Tensor         # int32 [B, 2, 100]  fertilized_until_day
    tcared: torch.Tensor        # bool  [B, 2, 100]  cared_today
    tfavail: torch.Tensor       # bool  [B, 2, 100]  fertilizer_available
    tcare: torch.Tensor         # int32 [B, 2, 100]  pending_care_bonus

    ux: torch.Tensor            # int32 [B, 2, U]    unit x  (U = 1 + MAX_HANDS)
    uy: torch.Tensor            # int32 [B, 2, U]
    n_hands: torch.Tensor       # int32 [B, 2]
    hires_today: torch.Tensor   # int32 [B, 2]
    land: torch.Tensor          # int32 [B, 2]  extra quadrants unlocked (0..3)

    shed: torch.Tensor          # int64 [B, 2, 12]
    seeds: torch.Tensor         # int64 [B, 2, 5]
    inv: torch.Tensor           # int64 [B, 2, U, 12]
    inv_order: torch.Tensor     # int64 [B, 2, U, 12]  dict-insertion tick

    # --- shared world ------------------------------------------------------
    market_inv: torch.Tensor    # int64 [B, 9]
    shops: torch.Tensor         # int64 [B, 8]  (alphabetical shop-instance counts)

    # --- rng ---------------------------------------------------------------
    rng_words: torch.Tensor     # int32 [B, 30, WORDS_PER_DAY] (may be empty)

    # --- diagnostics -------------------------------------------------------
    overflow: torch.Tensor      # int32 [B, 2]  hires dropped past MAX_HANDS

    # ---------------------------------------------------------------------- #
    def clone(self) -> "State":
        return replace(self, **{f.name: getattr(self, f.name).clone() for f in fields(self)})

    def to(self, device) -> "State":
        return replace(self, **{f.name: getattr(self, f.name).to(device) for f in fields(self)})

    def index(self, idx) -> "State":
        """Sub-batch view.  ``step`` is scalar and is passed through."""
        out = {}
        for f in fields(self):
            t = getattr(self, f.name)
            out[f.name] = t if t.dim() == 0 else t[idx]
        return replace(self, **out)

    @property
    def batch_size(self) -> int:
        return int(self.money.shape[0])

    @property
    def device(self):
        return self.money.device

    def tiles(self, field: str = "kind") -> torch.Tensor:
        """``[B, 2, 10, 10]`` view of a tile field, for human-readable dumps."""
        return getattr(self, field).reshape(*getattr(self, field).shape[:-1], 10, 10)

    # ---------------------------------------------------------------------- #
    @property
    def day(self) -> int:
        return int(self.step) // 24

    @property
    def hour(self) -> int:
        return int(self.step) % 24

    def market_price(self) -> torch.Tensor:
        """``[B, 9]`` int64 -- the source's ``market["prices"]``.

        Prices are a pure function of the (integer) market inventory, and the
        source refreshes them after every market slot and again at the end of
        ``_town_consume``, so they always equal ``f(inventory)`` when the step
        ends.  The table is built in pure Python with the source's own float64
        arithmetic and ``int(round(.))`` (round-half-to-even, NOT truncation), so
        this is bit-exact rather than merely close.
        """
        from ._tables import get_tables
        tab = get_tables(str(self.money.device))
        idx = (self.market_inv - tab.inv_lo).clamp(0, tab.inv_n - 1)
        return tab.price[torch.arange(idx.shape[-1], device=idx.device), idx]

    def unlocked_quadrants(self) -> torch.Tensor:
        """``[B, 2, 4]`` bool over (NW, NE, SW, SE).  NW is always unlocked and
        the rest are bought in the source's fixed LAND_ORDER, so the scalar
        ``land`` count determines the set."""
        k = torch.arange(4, device=self.land.device).view(1, 1, 4)
        return k <= self.land.unsqueeze(-1)

    def canonical(self) -> dict:
        """Every field WP1's differential test compares, as raw tensors.

        Nothing here is derived/normalised except ``prices`` and
        ``unlocked_quadrants``, which the source stores explicitly.
        """
        return {
            "step": self.step,
            "money": self.money,                       # int64 [B, 2]
            "kind": self.kind,
            "species": self.species,                   # crop id | animal idx
            "tday": self.tday,                         # planted_day | placed_day
            "tyield": self.tyield,                     # yield_units
            "tflag": self.tflag,                       # watered_today | fed_today
            "tcons": self.tcons,                       # consecutive_unwatered/unfed
            "tmls": self.tmls,                         # max_lifespan_step
            "tfert": self.tfert,                       # fertilized_until_day
            "tcared": self.tcared,                     # cared_today
            "tfavail": self.tfavail,                   # fertilizer_available
            "tcare": self.tcare,                       # pending_care_bonus
            "ux": self.ux, "uy": self.uy,
            "n_hands": self.n_hands,
            "hires_today": self.hires_today,
            "land": self.land,
            "unlocked_quadrants": self.unlocked_quadrants(),
            "shed": self.shed,
            "seeds": self.seeds,
            "inv": self.inv,
            "market_inv": self.market_inv,
            "prices": self.market_price(),             # int64 [B, 9]
            "shops": self.shops,
        }


@dataclass
class Actions:
    """Fixed-shape action tensors.

    ``farmer``  int16/int32 ``[B, 2, 3]``            (op_id, arg1, arg2)
    ``hands``   int16/int32 ``[B, 2, MAX_HANDS, 3]`` unused slots op_id = OP_PASS
    ``market``  int16/int32 ``[B, 2, MAX_ORDERS, 3]`` unused slots op_id = MKT_NONE
    """

    farmer: torch.Tensor
    hands: torch.Tensor
    market: torch.Tensor

    def unit_actions(self) -> torch.Tensor:
        """``[B, 2, 1 + MAX_HANDS, 3]`` int64 -- farmer first, then hands."""
        f = self.farmer.to(torch.int64).unsqueeze(2)
        h = self.hands.to(torch.int64)
        return torch.cat([f, h], dim=2)

    def to(self, device) -> "Actions":
        return Actions(self.farmer.to(device), self.hands.to(device), self.market.to(device))
