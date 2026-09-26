# T038 — Horizon own-feed WHEAT

Owner: codex. Started 2026-09-26. Human priority. Never submit to Kaggle.

## Hypothesis

Outside the fixed Horizon tape, existing finite-harvest planting planners can
turn harvested/empty owned tiles into WHEAT when a short-horizon feed deficit
is projected, reducing d10--29 `BUY_PRODUCT WHEAT`.  While that deficit
exists, harvested WHEAT should be reserved from discretionary sales.  The
layer must be default-off and action-identical to `es7_wm` when off.

## Method and gate

1. Map every non-tape `PLANT` and seed/replant decision in the frozen
   `es7_wm` source (tiles, dates, caps and controls), including EXP182 and
   CARROT2.
2. Implement the bounded gene above the frozen agent without modifying the
   fixed tape.  It may act only in addition to a parent `PASS`/eligible planner
   slot and must preserve parent actions/order otherwise.
3. Demonstrate genome-off action identity, run a fresh two-world, both-seat
   screen versus `es7_wm` (at most 8 workers), then run a fresh full panel only
   if that screen is positive and error-free.  Record every run in the ledger.

## Result

Pending.
