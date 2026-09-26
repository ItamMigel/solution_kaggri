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

### Planting/seed map of frozen `es7_wm` (`pkg/main.py`)

| Layer | Tiles it may use | When / cap | Actual authority |
|---|---|---|---|
| Native route tape | Route-selected precomputed tile positions only | All game; its `PLANT` and `BUY_SEED` quantities are fixed literals | Baseline WHEAT/CARROT planting; not a reactive layer. |
| V219 finite tomato | The ten third-land SE cells `(5..9, 5..6)` only | Plant d18; exactly 10 TOMATO seeds, only after NW/NE/SW, `money>=12000`, tomato >=$70, >=3 pizza/farmers shops and no native TOMATO/land obligation | Adds land, seed buy and dedicated hires; no WHEAT/replant authority. `main.py:1277-1476`. |
| EXP182/R51 input planner | Existing observed WHEAT/CARROT plant cells only; no empty cells | d12--28, hours 1--3; at most 2 new fertilizer workers, beam depth <=8 but a worker needs >=3 target cells | Forecasts gain from **FERTILIZE** only; it never emits PLANT or BUY_SEED. `:2160-2314`. |
| V9 CARROT | Only the current native route's WHEAT-PLANT cells | d10--23; may swap each currently planned WHEAT PLANT if CARROT/WHEAT >=1.8 and physical WHEAT >=40 (boom >=3.5 lowers reserve to 10); redirects matching seed orders | No new coordinates; earlier layer, normally subsumed by CARROT2. `:3048-3155`. |
| CARROT2 (final active swap) | Only current action's native WHEAT-PLANT cells, after confirming empty tile | d6--28; all qualifying same-turn tape WHEAT plants, bounded by spare CARROT seed; target float `_CA_BUFFER=9`; price `3*CARROT-20 > 4*WHEAT-10+_CA_MARGIN`; one-day feed reserve; money >= `_CA_CASH + 20q` | Replaces PLANT WHEAT with CARROT, trims WHEAT/CARROT buys and may add CARROT seeds; no new coordinates. `:4472-4726`, current knobs `:7649`. |
| Hybrid productive opening | One fixed `(2,4)` WHEAT cell | d0 PLANT, d0 one WHEAT seed; fixed hand route then water/harvest/restore pasture by d3 | Mutates the opening tape, not a general replant planner. `:6474-6618`. |
| E402 / seed-float trim | No tiles | E402 d26+; seed-float d27+ route 2 | Caps existing WHEAT/CARROT seed buys to remaining native tape PLANTs; it never creates a plant. `:6662-6714`, `:7126-7190`. |

The only non-tape free-cell crop program is V219, and it is TOMATO-only.  The
requested WHEAT lever therefore cannot be delegated to EXP182: that layer's
`input_forecast_wheat` means marginal harvest yield after fertilizer, not new
WHEAT planting.

### Implemented and evaluated

`lab/hplus/own_feed_wheat.py` builds `experiments/t038_own_feed/main_off.py`
and `main_on.py` from frozen `es7_wm` SHA-256 `d1220b…`.  Off returns the
parent action byte-for-byte.  On is d10--27 only and may use at most two
already-present WHEAT seeds per turn, solely by turning an inherited exact
`PASS` on an owned `None` tile into PLANT WHEAT after CARROT2's native
visit/yield model proves a future WATER/HARVEST route.  It adds no market buy,
hire, movement, hand or tape action.  A three-day visible-herd feed deficit is
`unfed_today + 2*all_animals - physical_WHEAT - actual_this-turn_WHEAT_buys`.
While positive, WHEAT SELL orders are replaced by empty slots, retaining slot
indices.

- Off identity: fresh seeds `295843440, 2062279317`, two complete official
  worlds versus `es7_wm`: **0/1,438 action diffs**, 4/4 DONE;
  `runs/t038_own_feed/identity.json`.
- Activation audit on the same two worlds: 0 plants, because no inherited PASS
  position had a native future WATER→HARVEST visit chain.  It did suppress 497
  WHEAT sale units across 67 turns; `runs/t038_own_feed/activation_mirror.json`.
- Fresh mandatory two-world both-seat screen versus Parthenos, with es7_wm
  control in the same invocation and eight workers: **8/8 valid/DONE**.
  Paired score is **0pp**, paired cash is **−$215.50** (whole-world 95% CI
  **−$429…−$2**); `runs/t038_own_feed/screen/`.

The screen is not positive, so the predeclared full panel was not run.  No
candidate, promotion or Kaggle action follows.
