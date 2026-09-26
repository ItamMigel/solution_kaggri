# T031 — wheat market arbitrage / counter-layer

Owner: codex. Started 2026-09-26. Deadline gate: 2026-09-28 18:00 UTC.

Hard rule: never submit to Kaggle. Kaggle access is read-only. Use at most eight workers.

## Questions

1. Re-execute the exact 39 T028 loss replays with market-action and town-consumption hooks. For each opponent, reconstruct WHEAT BUY_PRODUCT and SELL lots by action time/day, realised price and quantity; match purchases to later sales FIFO where possible. Quantify matched round-trip P&L, unsold inventory, price/time relation, and the incremental realised cost of our feed WHEAT.
2. If the mechanism is positive and actionably market-only, add an es6_c4g15 default-off wrapper with no unit actions: guarded WHEAT buy/sell thresholds by day/price/shed room, optionally early cheap feed reserve. Prove genome-off action identity; run a fresh two-world, both-seat screen against es6 at <=8 workers. Only a positive valid screen may enter the existing T025 full gate.

## Follow-up — claimed 2026-09-26 (Codex)

Claude requests two bounded checks, never a Kaggle submission and at most eight
workers from this task: (1) extend the exact replay-hook audit from the 39
losses to the same 39 losses plus 41 wins for **FERTILIZER**, the only other
`BUY_PRODUCT` item; establish whether opponents buy/sell it, at what time and
price, and whether a genuine market-only round trip or parent-compatible use
case exists.  A fertilizer market gene, if justified, is default-off and sits
above `es7_wm` / this task's `main_on.py`.  (2) screen 3--4 predeclared WHEAT
threshold variants against `es7_wm` on new two-world, both-seat mirrors,
varying buy/sell quote, day window and physical reserve.  Only a clear,
error-free improvement earns a later full gate against promoted `es7_wm`; no
candidate or submission follows from this follow-up alone.

## Predeclared interpretation

Classify as time arbitrage only if matched opponent purchases are materially cheaper than later sales after town consumption and their matched gross P&L is positive. Classify as price pumping only if opponents' BUY_PRODUCT WHEAT precedes a statistically/mechanistically higher realised WHEAT price for our FEED purchases than the control trajectory; do not confuse endogenous shared-price response with a proven causal counterfactual. Shop/route effects must be recorded separately.

## Result

### Replay timing / P&L (official engine 1.32.7)

`lab/tools/t031_wheat_arbitrage.py` re-executed exactly the 39 T028 loss replays with successful per-unit market hooks, including town-consumption price changes. The first implementation was discarded because farm→player mapping was incomplete; v3 was cross-checked on a replay against `replay_mine` (both player BUY_PRODUCT WHEAT count/cost exactly agree) and is the reported result: `runs/t031_wheat_arbitrage_v3/arbitrage.{json,md}`.

- Opponent WHEAT product buys average **1,074.69 u / $43,107.15** per loss at mean **d12.81 / $36.94**; WHEAT sells average **1,278.95 u / $51,303.51** at **d20.32 / $38.58**. Gross all-WHEAT cash flow is +$8,196.36/game, but that includes harvested WHEAT; do not call it pure arbitrage.
- Conservative FIFO temporal cash-flow matching pairs 1,073.18 purchased units to a *later* sale and gives **+$571.79/game**, average 76.71 steps held. Because farm output and purchased WHEAT are fungible, FIFO is a timing/accounting match, not proof of physical lot provenance. The positive buy→later-sale spread supports **time arbitrage/turnover**, not crop production.
- Town consumption raises the first post-buy price only +$0.56 on average, insufficient as a sole explanation. The conservative inter-turn accounting shadow removes a matched opponent purchase only while it remains outstanding (and deliberately ignores same-tick lockstep quotes); it prices our observed WHEAT product purchases at **+$624.77/game** relative to that shadow. Our actual product-WHEAT spend is $22,447.10/game. This is a shared-price *exposure* estimate, not a feasible behavioural counterfactual and not a causal claim that every dollar paid was feed.
- Classification: actionable timing turnover plus a plausible shared-price externality; **not a proven price-pump causal estimate**, and not a shop unlock or own-production explanation.

### Default-off market-only layer

Implemented `lab/hplus/wheat_market.py`, compiled builds `experiments/t031_wheat_market/main_off.py` and `main_on.py` (on SHA-256 `d1220b…`). It never changes `farmer`/`hands`; on only, it abstains if the parent already trades WHEAT and otherwise appends at most one order: a d6–17 cheap (`<= $30`) feed reserve up to 20 WHEAT, subject to $2,000 cash reserve, 8-unit cap and shed room; or a d10–28 high-price (`>= $40`) sale only above 35 physical WHEAT, 8-unit cap. `test_wheat_market.py` passes. Off action identity is **0 differences / 1,442 calls**, two whole games DONE: `runs/t031_wheat_market_identity.json`.

### Screens and gate

- Fresh two-world both-seat es6-mirror + Parthenos screen, seeds `1429496723, 605674921`, **16/16 valid/DONE**: market-on is **+0.250 paired score / +$15.25** vs es6 (`runs/t031_wheat_market_screen/`). This was positive, so it entered the full gate.
- Fresh disjoint T025-format full gate, 16 CSPRNG worlds × ten declared opponents × both seats, market-on and es6 in one invocation, four workers: **640/640 valid DONE**, zero errors; input hashes unchanged. Nine equal-weight strata yield **+4.167pp** paired score, **+3.125pp** one-sided 95% lower, cash **+$13.83**, and no named opponent below −10pp (all individual score estimates are non-negative). Evidence: `runs/t031_wheat_market_full_gate/gate_report.json`.

The numerical gate passes, but under the shared protocol it is only a review-ready WIP signal. Claude must independently review/reproduce before any `candidates_wip/` or candidate archive is created. No Kaggle submission occurred.

## Follow-up result — FERTILIZER audit and WHEAT sensitivity — 2026-09-26 (Codex)

`lab/tools/t031_wheat_arbitrage.py` now accepts the selected product and replay
outcome, and records actual `FERTILIZE` consumption by crop.  Official-engine
hooks re-executed the exact **80** T028 replays (the specified 39 losses + 41
wins) for FERTILIZER: `runs/t031_fertilizer_audit_v2/arbitrage.{json,md}`.
Opponents sell 340.81 FERTILIZER/game at d17.19 for $44.70/unit, then buy
90.00/game at d20.92 for $26.70/unit.  The 89.76 FIFO buy→later-sale matches
are **−$5.92/game**, not a positive round trip; a high total sale-minus-buy
cash-flow is fertilizer produced/collected before sale and must not be called
arbitrage.  Every replay has actual later consumption (118.38 `FERTILIZE`
units/game; 37.24 on WHEAT and 15.43 on CARROT), so late buying is a real
refill/use route, but it requires the existing pickup/unit tape.

Accordingly `experiments/t031_wheat_market/fertilizer_default_off.py` adds a
strict default-off top wrapper: when explicitly enabled it may append a cheap
late FERTILIZER buy only after the parent itself emits `PICKUP FERTILIZER`; it
never changes farmer/hands, does not sell, and abstains around any parent
FERTILIZER trade.  Genome-off is 4/4 draws against byte-identical es7_wm on
two fresh worlds/both seats (8/8 valid, zero cash difference):
`runs/t031_fertilizer_default_off_identity/`.  There is no enabled FERTILIZER
screen or gate because the audit has no positive market-only P&L.

The fresh CSPRNG two-world/both-seat WHEAT sensitivity screen
(`1851028621`, `331157374`; 20/20 valid) compares es7_wm with four
predeclared variants in `experiments/t031_wheat_market/variants/`:
wide buy (`d4–18, <=$32`), tight buy (`d8–16, <=$28`), 45-slot shed-room
reserve, and later/high sell (`d12–28, >=$42`).  The first three are exactly
inert (4/4 draws, paired score/cash 0); the sell variant is 0–2–2,
**−0.250 paired score / −$19.50**.  Best remains unchanged **es7_wm**;
there is no clear improvement and therefore no full gate, candidate change or
Kaggle action.  Evidence: `runs/t031_wheat_variant_screen/`.
