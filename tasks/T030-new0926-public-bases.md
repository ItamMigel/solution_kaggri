# T030 — new0926 public bases

Owner: codex.  Started 2026-09-26.

Goal: safely pause CMA4 at the current completed-generation boundary, recover the four remaining public notebook agents under `opponents/new0926/`, and classify their lineage before any evaluation decision.  Kaggle access is read-only; no submission.

Method: let the active CMA4 `gen_022` finish and verify `history.json`/`cma.pkl` before stopping its launcher; execute only notebook extraction/verification cells locally; download any declared Kaggle input dataset read-only; fingerprint emitted `main.py` for Horizon markers and structural origin.

## Result — notebook recovery and CMA pause 2026-09-26

- CMA4 completed gen-22 and gen-23 without errors (each 1,056 games), then stopped immediately after the atomic gen-23 pickle write: `history.json` has 24 records (last `gen=23`), `cma.pkl` has `countiter=24`, and `gen_024` is absent. `knob_cma.py` PID 630787 is deliberately `T` while its shell waits; resume exactly with `kill -CONT 630787`.
- Recovered + compiled (`py_compile`) `main.py`: four-turn forecast `b137c80d…`; master-engine-v3 `127ed3e6…`; v40 challenger `d5a192fa…`; Thomas 2944 `2714b6eb…`.
- Thomas metadata reports `dataset_sources=[]`: its inputs are read-only kernel outputs `thomastschinkel/the-2945-farm-96-vs-the-top-10-public-bots` and `statma/kaggriculture-herd-safe-sale-window-submit`. Their archive inner-source hashes matched `bfee70e9…` / `4889137f…` exactly.
- All recovered agents carry the same state-router/Horizon markers (`DEFAULT_SETTINGS`, `_R108_SHOP_ROUTES`, `_V92_TABLE`, `_V9_ITEM_HZ`, `make_agent`); Thomas runs Thomas before step 336 and HerdSafe afterwards. No independent base emerged. Of the initial nine, only God’s Mode and Hybu lack these markers, but the current screen makes both invalid (missing sibling imports / no final callable).


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

## Amendment — wheat source attribution / tape-safe repair 2026-09-26

Claim: codex. User-directed continuation. Kaggle remains read-only; no submission.

1. Re-execute the exact 39 T028 losses and all 41 available wins in official engine 1.32.7 with successful-action hooks. Per game/day record WHEAT plants, harvest tiles/units, EOD WHEAT tiles, quadrants, hands, WHEAT seed and product purchases/cost, and successful FEED. Do not infer these from final inventory.
2. Explain the loss-vs-win contrast and whether opponents' WHEAT sales are production, land/labour, or avoided purchased feed.
3. Implement only the smallest evidence-supported, tape-safe, **default-off** gene on the working es6 archive; prove genome-off action identity; run a fresh both-seat 2-world screen at <=8 workers. Only a positive valid screen may use T025's fresh full-panel gate against es6.

## Result — wheat source attribution / idle-crop gene rejected 2026-09-26

`lab/tools/t030_wheat_sources.py` re-executed all 80 available T028 worlds (exactly 39 losses and 41 wins) in official engine 1.32.7, with eight processes and zero miner failures. It records only successful actions. Full daily matrix: `runs/t030_wheat_sources_v2/wheat.json` / `.md`.

- **Losses:** opponent WHEAT sold is +516.97 units/game, but it does *not* arise from more WHEAT crop production: opponent−us is **−7.62 planted tiles** and **−8.00 harvested units**. WHEAT seed buying is also lower by 5.95 units ($59.49). Instead the opponent executes **+528.67 BUY_PRODUCT WHEAT**, $20,660/game more cost; successful FEED is only +4.97.
- **Daily mechanism:** quadrants converge at roughly 3.1--3.2 after d11; successful daily hires differ little (seasonal +3.97 for opponent). From d10--27 the opponent repeatedly spends much more on purchased WHEAT while WHEAT crop stock/harvest is comparable or lower. This supports purchased/re-sold market turnover rather than a own-feed/land/labour explanation. In the 41 wins the corresponding purchase-cost gap falls to $2,114/game and sales gap to 46.8 units.
- Implemented `lab/hplus/wheat_idle.py`, a namespaced default-off gene over sealed es6. When on, it only turns an inherited exact `PASS` into `PLANT WHEAT` on an already empty unlocked tile, using only an already-present WHEAT seed after reserving the parent's planned WHEAT plants. It never changes market orders, money, movement, hire, hand count, or a non-PASS action. The off build has **0 action differences / 1,442 calls**, both games DONE: `runs/t030_wheat_idle_identity.json`.
- Fresh screen (`runs/t030_wheat_idle_screen`, seeds `870722613,787550011`, both seats vs es6 mirror + Parthenos, <=8 workers): **16/16 valid**, on candidate **0/8**, paired vs es6 **−0.500 score** (95% −0.75..−0.25), **−$2,248.25** (95% −$3,092.50..−$1,404.00). It is rejected; no full T025 gate, candidate, or Kaggle action.
