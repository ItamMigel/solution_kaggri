"""GPU-vectorised kaggriculture.

``VecKaggriculture`` reproduces
``kaggle_environments/envs/kaggriculture/kaggriculture.py`` step for step, with a
leading batch dimension on every tensor.  There is no Python loop over envs; the
loops that do exist mirror sequential semantics the source really has (unit
order, market order index, market lockstep rounds) and are each a small number of
fully batched passes.

    env = VecKaggriculture(n_envs=4096, device="cuda")
    st = env.reset(torch.arange(4096))
    st, reward, done, info = env.step(st, actions)

``seeds`` are the values the real env stores in ``env.info["seed"]``.

Deviations from the reference (all deliberate, none reachable by the agents in
our corpus -- see the report):

* Only the **default configuration** is modelled (boardSize 10, startingMoney
  3000, turnsPerDay 24, shedCapacity 100, weedSpawnChance 0.005, the town
  intervals, farmHandCostMult 1, and the built-in ``MARKET_PARAMS``).  A
  ``marketParams`` override in the configuration is NOT honoured.
* Hires past ``max_hands`` still cost money and still bump ``hires_today``
  (faithful), but the extra hand is not created; ``State.overflow`` counts them.
  The default cap is 16 == the contract's ``MAX_HANDS``; the observed maximum in
  the differential-test corpus is 17, so construct with a larger ``max_hands``
  if an agent hires more aggressively.
* Market orders past slot ``max_orders`` (10) are dropped, exactly as the source
  does (``q[:max_orders]``).
* The source aborts a market lane after 100 000 lockstep rounds with a warning;
  the closed-form fast path has no such cut-off.  Reaching it needs a single
  order for >100 000 units that can actually all commit, which no reachable
  money/shed state allows.
"""

from __future__ import annotations

from typing import Optional

import torch

from . import ops as O
from . import _mt19937 as MT
from ._consts import (BOARD_SIZE, HALF, LAST_STEP, MARKET_I0, N_DAYS, N_TILES,
                      QUADRANT_MASK, STARTING_MONEY, TOWN_SHOP_UNLOCK_INTERVAL,
                      TURNS_PER_DAY)
from ._daily import decay_plants, end_of_day, town_consume
from ._market import (N_SLOT_FLAGS, market_slot_static, process_market,
                      slot_flags)
from ._state import Actions, State
from ._units import _ORDER_SENTINEL, apply_unit_actions, plant_blocked

OBS_DIM = 64


class VecKaggriculture:
    def __init__(self, n_envs: int, device: str = "cuda", dtype=torch.float32,
                 max_hands: int = O.MAX_HANDS, max_orders: int = O.MAX_ORDERS,
                 collect_stats: bool = False, cuda_graph: Optional[bool] = None,
                 market_exact_loop: bool = False, rng_lazy: Optional[bool] = None,
                 rng_budget_bytes: int = 1 << 30):
        self.n_envs = int(n_envs)
        self.device = torch.device(device)
        self.dtype = dtype
        self.max_hands = int(max_hands)
        self.max_units = self.max_hands + 1
        self.max_orders = int(max_orders)
        self.collect_stats = collect_stats
        self.market_exact_loop = bool(market_exact_loop)
        if rng_lazy is None:
            rng_lazy = (self.n_envs * N_DAYS * MT.WORDS_PER_DAY * 4) > rng_budget_bytes
        self.rng_lazy = bool(rng_lazy)
        self.stats: dict = {}
        if cuda_graph is None:
            cuda_graph = self.device.type == "cuda"
        self.cuda_graph = bool(cuda_graph) and self.device.type == "cuda"
        self._graphs = {}
        self._graph_pool = None
        self._graph_key = None
        dev = self.device
        self._day_t = torch.zeros((), dtype=torch.int64, device=dev)
        self._step_t = torch.zeros((), dtype=torch.int64, device=dev)
        self._ua_buf = torch.zeros((self.n_envs, 2, self.max_units, 3),
                                   dtype=torch.int64, device=dev)
        self._blocked_buf = torch.zeros((self.n_envs, 2, O.N_CROPS),
                                        dtype=torch.bool, device=dev)
        self._rungs = self._build_ladder()
        # buffers for the graph-captured market / daily phases
        self._slot_buf = torch.zeros((self.n_envs, 2, 3), dtype=torch.int64, device=dev)
        self._unlock_t = torch.zeros((), dtype=torch.bool, device=dev)
        self._mkt_graph = None
        self._daily_graph = None
        self._eod_graph = None
        # predicted ladder rung for the next step (hand counts move slowly, so
        # last step's rung is nearly always right; a miss just costs one extra
        # graph replay and is still exact)
        self._pred_rung = self.max_units
        # measured a wash at B=4096 (13.17 vs 13.65 ms/step, clocks pinned,
        # interleaved repeats); off keeps the captured-graph set smaller.
        self.speculative_rung = False
        # pinned staging buffer + event for the one device->host read per step.
        # A plain .to("cpu") (even non_blocking) on unpinned memory is a hard
        # sync; pinned + event lets the copy overlap the unit-phase graph.
        if self.device.type == "cuda":
            self._pin = torch.empty(self.max_orders * N_SLOT_FLAGS + 1,
                                    dtype=torch.int64).pin_memory()
            self._evt = torch.cuda.Event()
        else:
            self._pin = None
            self._evt = None

    # ------------------------------------------------------------------ #
    _MUTABLE = ("kind", "species", "tday", "tyield", "tflag", "tcons", "tmls",
                "tfert", "tcared", "tfavail", "tcare", "ux", "uy", "shed",
                "seeds", "inv", "inv_order")

    def _unit_phase(self, st: State, lo: int = 0, hi: Optional[int] = None):
        """Apply unit passes [lo, hi).  Running MORE passes than there are hands
        is a provable no-op (`exists = n_hands >= u` masks the whole body), which
        is what lets the prefix be enqueued before the host knows the true count."""
        from ._units import apply_one_unit
        if lo == 0:
            plant_blocked(self._ua_buf, st.seeds, out=self._blocked_buf)
        for u in range(lo, self.max_units if hi is None else hi):
            apply_one_unit(st, self._ua_buf, self._blocked_buf,
                           self._day_t, self._step_t, u)

    def _build_ladder(self) -> tuple:
        """Graph sizes to capture.  Hands are dismissed every night and re-hired
        through the day, so most steps need far fewer than ``max_units`` passes.
        The rungs stay ~4 apart at any ``max_hands`` so a wide env (WP3 trains at
        ``max_hands=24``) never falls off a cliff from 13 straight to 25."""
        rungs = {1, self.max_units}
        k = 3
        while k < self.max_units:
            rungs.add(k)
            k += 4
        return tuple(sorted(rungs))

    def _ladder(self, need: int) -> int:
        for k in self._rungs:
            if k >= need:
                return k
        return self.max_units

    # every field the captured phases mutate (step/seed/rng_words/done never are)
    _MUTABLE_ALL = _MUTABLE + ("money", "n_hands", "hires_today", "land",
                               "market_inv", "shops", "overflow")

    def _capture_fn(self, st: State, fn, fields):
        """Record ``fn`` into a CUDA graph.  Warm-up executes (and so mutates)
        the state, so snapshot/restore around it; capture itself only records."""
        saved = {f: getattr(st, f).clone() for f in fields}
        s = torch.cuda.Stream()
        s.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(s):
            for _ in range(3):
                fn()
        torch.cuda.current_stream().wait_stream(s)
        for f, v in saved.items():
            getattr(st, f).copy_(v)
        g = torch.cuda.CUDAGraph()
        if self._graph_pool is None:
            with torch.cuda.graph(g):
                fn()
            self._graph_pool = g.pool()
        else:
            with torch.cuda.graph(g, pool=self._graph_pool):
                fn()
        return g

    def _capture(self, st: State, lo: int, hi: int):
        g = self._capture_fn(st, lambda: self._unit_phase(st, lo, hi), self._MUTABLE)
        self._graphs[(lo, hi)] = g
        return g

    def _state_key(self, st: State) -> tuple:
        """Identity of the exact buffers the captured graphs write into."""
        return tuple(getattr(st, f).data_ptr() for f in self._MUTABLE_ALL) + (
            st.rng_words.data_ptr(), st.seed.data_ptr())

    def _unit_graph(self, st: State, lo: int, hi: int):
        g = self._graphs.get((lo, hi))
        if g is None:
            g = self._capture(st, lo, hi)
        g.replay()

    # ---- market slot -------------------------------------------------- #
    def _market_slot(self, st: State, slot: torch.Tensor):
        self._slot_buf.copy_(slot)
        if self._mkt_graph is None:
            self._mkt_graph = self._capture_fn(
                st, lambda: market_slot_static(st, self._slot_buf, self.max_hands),
                self._MUTABLE_ALL)
        self._mkt_graph.replay()

    # ---- town consumption + plant decay ------------------------------- #
    def _daily_phase(self, st: State):
        town_consume(st, self._step_t, self._day_t)
        decay_plants(st, self._step_t)

    def _run_daily(self, st: State):
        if not self.cuda_graph:
            return self._daily_phase(st)
        if self._daily_graph is None:
            self._daily_graph = self._capture_fn(st, lambda: self._daily_phase(st),
                                                 self._MUTABLE_ALL)
        self._daily_graph.replay()

    # ---- end of day ---------------------------------------------------- #
    def _eod_phase(self, st: State):
        words = (MT.gen_words((st.seed * 1_000_003) ^ self._day_t) if self.rng_lazy
                 else None)
        end_of_day(st, self._day_t, self.max_hands, words, self._unlock_t)

    def _run_eod(self, st: State, day: int):
        unlock = (day + 1) % TOWN_SHOP_UNLOCK_INTERVAL == 0 and (day + 1) > 0
        if not self.cuda_graph:
            words = (MT.gen_words((st.seed * 1_000_003) ^ day) if self.rng_lazy
                     else None)
            return end_of_day(st, day, self.max_hands, words, unlock)
        self._unlock_t.fill_(unlock)
        if self._eod_graph is None:
            self._eod_graph = self._capture_fn(st, lambda: self._eod_phase(st),
                                               self._MUTABLE_ALL)
        self._eod_graph.replay()

    # ------------------------------------------------------------------ #
    def reset(self, seeds: torch.Tensor, rng: bool = True) -> State:
        b = self.n_envs
        dev = self.device
        assert seeds.numel() == b, f"expected {b} seeds, got {seeds.numel()}"
        seeds = seeds.to(dev, torch.int64).reshape(b)

        def z(shape, dtype):
            return torch.zeros(shape, dtype=dtype, device=dev)

        kind = torch.full((b, 2, N_TILES), O.TILE_LOCKED, dtype=torch.int32, device=dev)
        nw = torch.tensor(QUADRANT_MASK[0], dtype=torch.bool, device=dev)
        kind[:, :, nw] = O.TILE_EMPTY

        st = State(
            # kept on the host: int(step) is read every step and a device
            # scalar would cost a full sync each time.
            step=torch.zeros((), dtype=torch.int64),
            seed=seeds,
            done=z((b,), torch.bool),
            money=torch.full((b, 2), STARTING_MONEY, dtype=torch.int64, device=dev),
            kind=kind,
            species=z((b, 2, N_TILES), torch.int32),
            tday=z((b, 2, N_TILES), torch.int32),
            tyield=z((b, 2, N_TILES), torch.int32),
            tflag=z((b, 2, N_TILES), torch.bool),
            tcons=z((b, 2, N_TILES), torch.int32),
            tmls=z((b, 2, N_TILES), torch.int32),
            tfert=z((b, 2, N_TILES), torch.int32),
            tcared=z((b, 2, N_TILES), torch.bool),
            tfavail=z((b, 2, N_TILES), torch.bool),
            tcare=z((b, 2, N_TILES), torch.int32),
            ux=torch.full((b, 2, self.max_units), HALF - 1, dtype=torch.int32, device=dev),
            uy=torch.full((b, 2, self.max_units), HALF - 1, dtype=torch.int32, device=dev),
            n_hands=z((b, 2), torch.int32),
            hires_today=z((b, 2), torch.int32),
            land=z((b, 2), torch.int32),
            shed=z((b, 2, O.N_ITEMS), torch.int64),
            seeds=z((b, 2, O.N_CROPS), torch.int64),
            inv=z((b, 2, self.max_units, O.N_ITEMS), torch.int64),
            inv_order=torch.full((b, 2, self.max_units, O.N_ITEMS), _ORDER_SENTINEL,
                                 dtype=torch.int64, device=dev),
            market_inv=torch.full((b, O.N_PRODUCTS), MARKET_I0, dtype=torch.int64, device=dev),
            shops=z((b, 8), torch.int64),
            rng_words=(self._make_rng(seeds) if (rng and not self.rng_lazy)
                       else torch.zeros((b, N_DAYS, 1), dtype=torch.int32, device=dev)),
            overflow=z((b, 2), torch.int32),
        )
        return st

    def _make_rng(self, seeds: torch.Tensor, chunk_rows: int = 32768) -> torch.Tensor:
        b = seeds.shape[0]
        days = torch.arange(N_DAYS, device=seeds.device, dtype=torch.int64)
        seed_day = (seeds.unsqueeze(1) * 1_000_003) ^ days.unsqueeze(0)   # [B, 30]
        flat = seed_day.reshape(-1)
        out = torch.empty((flat.shape[0], MT.WORDS_PER_DAY), dtype=torch.int32,
                          device=seeds.device)
        for s in range(0, flat.shape[0], chunk_rows):
            e = min(s + chunk_rows, flat.shape[0])
            out[s:e] = MT.gen_words(flat[s:e]).to(torch.int32)
        return out.reshape(b, N_DAYS, MT.WORDS_PER_DAY)

    # ------------------------------------------------------------------ #
    def step(self, state: State, actions: Actions):
        st = state
        t = int(st.step)
        day = t // TURNS_PER_DAY
        stats = self.stats if self.collect_stats else None

        ua = actions.unit_actions()                       # [B, 2, U, 3] int64
        self._day_t.fill_(day)
        self._step_t.fill_(t)

        mkt = actions.market.to(torch.int64)
        # ONE device->host transfer per step: the market slot flags (action-only)
        # and the number of unit passes the CUDA-graph ladder needs.  It is
        # ENQUEUED here but only read after the unit-phase graph has been issued,
        # so the GPU has a full unit phase of work to chew on while the host
        # waits -- otherwise the sync serialises CPU issue and GPU execution and
        # costs ~66% of the step.
        n_slots = min(mkt.shape[2], self.max_orders)
        gpu_packed = torch.cat([slot_flags(mkt).reshape(-1).to(torch.int64),
                                st.n_hands.max().reshape(1).to(torch.int64)])
        n_packed = n_slots * N_SLOT_FLAGS + 1

        if self.cuda_graph:
            key = self._state_key(st)
            if self._graph_key != key:
                # Captured graphs bake in tensor ADDRESSES.  Keying on a single
                # tensor is unsound: a freed State's allocation can be handed
                # straight back for the next one, so kind.data_ptr() can match
                # while every other buffer moved.  Key on all of them.
                self._graphs.clear()
                self._mkt_graph = self._daily_graph = self._eod_graph = None
                self._graph_pool = None
                self._pred_rung = self.max_units
                self._graph_key = key
            host = self._pin[:n_packed]
            host.copy_(gpu_packed, non_blocking=True)
            self._evt.record()
            self._ua_buf.copy_(ua)
            if self.speculative_rung:
                # Issue a predicted unit phase BEFORE reading the copy so the GPU
                # has work queued while the host waits.  Over-running the rung is
                # a provable no-op, so a mispredict only costs an extra replay.
                self._unit_graph(st, 0, self._pred_rung)
            self._evt.synchronize()
            packed = host.tolist()
            flags = [packed[i * N_SLOT_FLAGS:(i + 1) * N_SLOT_FLAGS]
                     for i in range(n_slots)]
            need = int(packed[-1]) + 1
            rung = self._ladder(need)
            if not self.speculative_rung:
                self._unit_graph(st, 0, rung)
            elif rung > self._pred_rung:
                # mispredict: finish the exact remainder, never the whole width
                self._unit_graph(st, self._pred_rung, rung)
            # n_hands grows by at most one per HIRE-carrying slot per player, so
            # bias the next prediction upward by that much.
            n_hire = sum(1 for f in flags if f[1])
            self._pred_rung = self._ladder(min(need + n_hire, self.max_units))
        else:
            packed = gpu_packed.tolist()
            flags = [packed[i * N_SLOT_FLAGS:(i + 1) * N_SLOT_FLAGS]
                     for i in range(n_slots)]
            blocked = plant_blocked(ua, st.seeds)
            active = (ua[..., 0] != O.OP_PASS).any(dim=1).any(dim=0)   # [U]
            for u, on in enumerate(active.tolist()):
                if on or u == 0:
                    from ._units import apply_one_unit
                    apply_one_unit(st, ua, blocked, self._day_t, self._step_t, u)

        process_market(st, mkt, self.max_hands, stats,
                       exact_loop=self.market_exact_loop, flags=flags,
                       graph_slot=((lambda sl: self._market_slot(st, sl))
                                   if self.cuda_graph else None))
        self._run_daily(st)
        if (t + 1) % TURNS_PER_DAY == 0:
            self._run_eod(st, day)

        st.step = st.step + 1
        done_now = t >= LAST_STEP
        st.done = torch.full_like(st.done, done_now)
        if done_now:
            reward = (st.money[:, 0] - st.money[:, 1]).to(torch.float32)
        else:
            reward = torch.zeros(st.money.shape[0], dtype=torch.float32, device=st.money.device)
        info = {"money": st.money, "overflow": st.overflow}
        return st, reward, st.done, info

    # ------------------------------------------------------------------ #
    def observe(self, state: State, player: int) -> torch.Tensor:
        """A small default observation -- a *convenience wrapper only*.

        WP3 owns observation design and should build features straight off the
        raw tensors in ``State`` / ``State.canonical()`` (both players' tiles,
        inventories, market inventory and prices, shops, ...).  Nothing in the
        env depends on this method."""
        st = state
        b = st.money.shape[0]
        me, opp = player, 1 - player
        t = int(st.step)
        day = t // TURNS_PER_DAY
        parts = [
            (st.money[:, me].to(torch.float32) / 1e4).unsqueeze(-1),
            (st.money[:, opp].to(torch.float32) / 1e4).unsqueeze(-1),
            torch.full((b, 1), day / 30.0, device=st.money.device),
            torch.full((b, 1), (t % TURNS_PER_DAY) / 24.0, device=st.money.device),
            st.shed[:, me].to(torch.float32) / 100.0,
            st.seeds[:, me].to(torch.float32) / 10.0,
            st.market_inv.to(torch.float32).sub(MARKET_I0).div(500.0),
            st.shops.to(torch.float32),
            st.land[:, me].to(torch.float32).unsqueeze(-1),
            st.n_hands[:, me].to(torch.float32).unsqueeze(-1) / 16.0,
            torch.stack([(st.kind[:, me] == k).sum(-1) for k in range(7)], -1).float() / 100.0,
        ]
        out = torch.cat(parts, dim=-1)
        if out.shape[-1] < OBS_DIM:
            out = torch.cat([out, torch.zeros(b, OBS_DIM - out.shape[-1],
                                              device=out.device)], dim=-1)
        return out[:, :OBS_DIM]

    # ------------------------------------------------------------------ #
    # WP1 fidelity-gate surface: spec.md §14 canonical schema.
    _SHOPS_ALPHA_TO_DICT = (0, 2, 7, 4, 5, 1, 6, 3)

    def canonical(self, state: State) -> dict:
        """Full comparable state in WP1's schema (spec.md §14).

        ``mkt_price`` comes from the tensor price table, so the price curve --
        float64 with ``int(round(.))``, round-half-to-even, NOT truncation -- is
        under test rather than being re-derived by the harness.
        """
        st = state
        b = st.money.shape[0]
        dev = st.money.device
        t = int(st.step)

        is_plant = st.kind == O.TILE_PLANT
        is_animal = st.kind == O.TILE_ANIMAL
        live = is_plant | is_animal
        neg1 = torch.full_like(st.kind, -1)
        planes = [
            st.kind,
            torch.where(is_plant, st.species, neg1),                 # crop
            torch.where(is_animal, st.species, neg1),                # animal
            torch.where(live, st.tday, neg1),                        # day0
            st.tflag.to(st.kind.dtype),
            st.tcons,
            st.tyield,
            torch.where(is_plant, st.tmls, neg1),
            torch.where(is_plant, st.tfert, neg1),
            st.tcared.to(st.kind.dtype),
            st.tfavail.to(st.kind.dtype),
            st.tcare,
        ]
        tiles = torch.stack(planes, dim=-1).reshape(b, 2, 10, 10, 12).to(torch.int16)

        n_hands = st.n_hands.to(torch.int64)
        nh = min(self.max_hands, 16)
        hx = st.ux[:, :, 1:1 + nh].to(torch.int64)
        hy = st.uy[:, :, 1:1 + nh].to(torch.int64)
        hlive = torch.arange(nh, device=dev).view(1, 1, -1) < n_hands.unsqueeze(-1)
        hands = torch.stack([torch.where(hlive, hx, -1), torch.where(hlive, hy, -1)], -1)
        if nh < 16:
            hands = torch.cat([hands, torch.full((b, 2, 16 - nh, 2), -1,
                                                 dtype=hands.dtype, device=dev)], dim=2)

        inv = st.inv[:, :, :17]
        if inv.shape[2] < 17:
            inv = torch.cat([inv, torch.zeros((b, 2, 17 - inv.shape[2], O.N_ITEMS),
                                              dtype=inv.dtype, device=dev)], dim=2)

        bits = torch.zeros(b, dtype=torch.int64, device=dev)
        for j, src in enumerate(self._SHOPS_ALPHA_TO_DICT):
            bits |= (st.shops[:, j] > 0).to(torch.int64) << src

        return {
            "money": st.money.to(torch.int64),
            "farmer": torch.stack([st.ux[:, :, 0], st.uy[:, :, 0]], -1).to(torch.int16),
            "n_hands": st.n_hands.to(torch.int16),
            "hands": hands.to(torch.int16),
            "hires_today": st.hires_today.to(torch.int16),
            "n_land": st.land.to(torch.int16),
            "shed": st.shed.to(torch.int32),
            "seeds": st.seeds.to(torch.int32),
            "inv": inv.to(torch.int32),
            "tiles": tiles,
            "mkt_inv": st.market_inv.to(torch.int32),
            "mkt_price": st.market_price().to(torch.int32),
            "shops": bits.to(torch.int32),
            "day": torch.full((b,), t // TURNS_PER_DAY, dtype=torch.int16, device=dev),
            "hour": torch.full((b,), t % TURNS_PER_DAY, dtype=torch.int16, device=dev),
            "step": torch.full((b,), t, dtype=torch.int32, device=dev),
        }

    # ------------------------------------------------------------------ #
    def empty_actions(self, device: Optional[torch.device] = None) -> Actions:
        dev = device or self.device
        b = self.n_envs
        farmer = torch.zeros((b, 2, 3), dtype=torch.int32, device=dev)
        hands = torch.zeros((b, 2, self.max_hands, 3), dtype=torch.int32, device=dev)
        market = torch.zeros((b, 2, self.max_orders, 3), dtype=torch.int32, device=dev)
        return Actions(farmer, hands, market)
