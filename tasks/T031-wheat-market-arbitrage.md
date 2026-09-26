# T031 — wheat market arbitrage / counter-layer

Owner: codex. Started 2026-09-26. Deadline gate: 2026-09-28 18:00 UTC.

Hard rule: never submit to Kaggle. Kaggle access is read-only. Use at most eight workers.

## Questions

1. Re-execute the exact 39 T028 loss replays with market-action and town-consumption hooks. For each opponent, reconstruct WHEAT BUY_PRODUCT and SELL lots by action time/day, realised price and quantity; match purchases to later sales FIFO where possible. Quantify matched round-trip P&L, unsold inventory, price/time relation, and the incremental realised cost of our feed WHEAT.
2. If the mechanism is positive and actionably market-only, add an es6_c4g15 default-off wrapper with no unit actions: guarded WHEAT buy/sell thresholds by day/price/shed room, optionally early cheap feed reserve. Prove genome-off action identity; run a fresh two-world, both-seat screen against es6 at <=8 workers. Only a positive valid screen may enter the existing T025 full gate.

## Predeclared interpretation

Classify as time arbitrage only if matched opponent purchases are materially cheaper than later sales after town consumption and their matched gross P&L is positive. Classify as price pumping only if opponents' BUY_PRODUCT WHEAT precedes a statistically/mechanistically higher realised WHEAT price for our FEED purchases than the control trajectory; do not confuse endogenous shared-price response with a proven causal counterfactual. Shop/route effects must be recorded separately.

## Result

Pending.
