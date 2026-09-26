# T030 — new0926 public bases

Owner: codex.  Started 2026-09-26.

Goal: safely pause CMA4 at the current completed-generation boundary, recover the four remaining public notebook agents under `opponents/new0926/`, and classify their lineage before any evaluation decision.  Kaggle access is read-only; no submission.

Method: let the active CMA4 `gen_022` finish and verify `history.json`/`cma.pkl` before stopping its launcher; execute only notebook extraction/verification cells locally; download any declared Kaggle input dataset read-only; fingerprint emitted `main.py` for Horizon markers and structural origin.


## Amendment 2026-09-26 — demand timing and ladder market audit

Claim: codex.  User-directed follow-on; Kaggle is read-only and no submission.

1. Diff `opponents/new0926/demand-preserving-turn-sale-timing/main.py` against
`agents/horizon_v5_market.py` and promoted `candidates/es6_c4g15/pkg/main.py`; isolate
the market demand/sale-timing layer.
2. Transplant the isolated layer as a default-off, identity-audited gene into an es6-based
agent (or use its base with es6 knobs and COLLECT), then run a paired, both-seat screen
vs es6 at <=8 workers. Claude's independent 16-world/10-opponent gate is at
`runs/gate_demand_vs_es6`; it must not be overwritten.
3. From the 39 losses in `replays/t028`, mine per crop/day first seller, realized prices
for each side, and contested shops, to distinguish price/demand competition from other
causes. Report durable facts via `bin/say claude`.

## Result — market audit 2026-09-26

All 39 losses were re-executed with official-engine `_commit_unit` hooks (zero miner failures). The market is shared and sales are often simultaneous, but it is not primarily a sale-order/price failure: WHEAT is −20,162 realised units and −$794,851 gross aggregate versus opponents at a *slightly higher* own mean price (+$0.47); carrot/egg/fertilizer similarly lose volume with near-equal prices. Strawberry is the exception (+159 units but −$6.40/unit, −$41,367 gross), so it is a conditional research lead only. Full table and day rows: `research/t030_market_losses.md`, `runs/t030_market_losses/market.json`.

## Result — demand-layer diff / implementation status 2026-09-26

`demand-preserving-turn-sale-timing` is a Horizon fork (same base through its early V9/route stack). Its explicit timing layers are: (a) ADV moves ready cash products planned 3 ticks ahead into an earlier SELL (from d9; preserves the next tick's funding sale), (b) a fallback lockstep order-book permutation of existing SELL/fixed orders, and (c) extra experimental lead-sell/time-window wrappers. Es6 already contains a stronger ADV (lookahead 20 ticks, from d6), its own queue-hole closure and COLLECT; the public FLOWPX rival-flow trigger is disabled by `_FX_FLOW_MIN=999`. Thus the only clean missing transfer is the within-tick order-book permutation.

Built a default-off `DMX` version in Codex worktree, but its loader integration is not yet valid: three 4-world screens and the 1-world off identity run reveal the copied archive executes PASS ($3k), whereas source es6 earns $140–188k. This is an archive entrypoint/export binding issue, not an evidence result; those runs are explicitly invalid for DMX. Do not promote/race it. Claude's independent full demand-vs-es6 run remains untouched at `runs/gate_demand_vs_es6`.
