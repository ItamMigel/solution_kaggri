# T028 — capability gap: top-20 versus es3_g5

_2026-09-26, Codex.  Kaggle was used read-only; no submission was made._

## Data and scope

The requested direct cohort does not exist: the 142 `COMPLETED` episodes of
es3_g5 submission `56555111` have **zero** episode-ID intersections with the
current top-20 teams' submissions (each team's submission list and episode
list was queried).  Therefore there is no valid same-world top-minus-es3
comparison for this submission.

As a clearly labelled, non-causal fallback, we re-executed 80 recent es3_g5
replays and one latest completed replay for each current top-20 team (19 files:
one download overlapped).  `replay_mine` used the official 1.32.7 engine,
with 8 processes, and yielded zero mining errors.  The two sets have different
opponents/worlds, so the table ranks hypotheses, not an estimated intervention
effect.

## Ranked dollar gap (top-20 sample minus es3_g5 sample)

| rank | realised source | top mean $ | es3 mean $ | difference/game | structural evidence |
|---:|---|---:|---:|---:|---|
| 1 | EGG sales | 8,480 | 3,528 | **+4,952** | geese: 5.9 versus 2.2 from d11 onward |
| 2 | TOMATO sales | 5,114 | 1,942 | **+3,171** | top sells from d18; ours only from d26 |
| 3 | WOOL sales | 21,834 | 20,433 | +1,401 | not a primary missing capability |
| 4 | CARROT sales | 7,818 | 6,441 | +1,378 | additional seed/mix choice |
| 5 | WHEAT sales | 25,186 | 24,571 | +614 | small |
| 6 | STRAWBERRY sales | 25,958 | 29,525 | −3,566 | es3 already over-indexes here |
| 7 | purchased wheat cost | 12,253 | 15,899 | **−3,646** | likely consequence of a different herd/crop plan |

Mean final cash is $106,074 (top, n=19) versus $98,345 (es3, n=80), an
unpaired +$7,728.  The source rows are not additive: market price endogenous
effects and all other spending remain in final cash.

## What the leaders actually do

The egg gap is a complete early goose programme, not a late market order:

* Top sample buys geese and builds coops primarily on d6--11: mean goose tiles
  reach 2.0 on d6, 4.7 on d9, and 5.9 on d11.  es3 reaches only 0.6 on d6,
  2.2 on d11, then stays near that level.
* Top egg sales begin on d6 and are 10--15 units/day from d14 onward; es3
  begins materially on d11 and remains mostly 2--6 units/day.
* The leaders execute 7 BUILD_COOP versus 4, 363 FEED versus 332, 524 HARVEST
  versus 484, and 214 FERTILIZE versus 114 actions/game.  Their plant
  fertilisation begins d10, but it is a secondary correlated signal here.
* A goose produces from four days after placement, once daily; with care it can
  yield two eggs.  Thus a d6--9 build/placement route is required to explain
  the d11--14 sales; adding a goose after the tape's current placements leaves
  it in the shed and is a cash leak.

## Recommended module: G1 `early_goose_microplan`

Add a default-off, audited **route-owned** microplan, not a market-only patch.
At the existing early animal route (d6--11), it should reserve orders/cash,
construct two additional coops on exact empty tiles, pick up/place a bounded
four additional geese, then own their feed/care/harvest/drop path and sell only
extra eggs at existing sale slots.  It must abort on any observed-state or
parent-action mismatch and then return to unmodified Horizon.  Restrict initial
screen variants to total goose targets 4/5/6, with no land, hand or fertilizer
policy change.

This is deliberately different from prior negatives: T012 rejected an
unexecutable market-only crop overlay; T021 required a full goose microplan but
did not implement/race one; T021's fertilizer hand and T023's PASS→WATER/CARE/
FEED modules were isolated operations; T014 changed only final-day hire ratio.
The data says the missing sequence is early capacity + placement + daily
service, which none of those modules supplied.

Gate: genome-off byte-identical to `es5_c3g15`; fixed-state trace audit must
show zero illegal/rejected overrides.  Screen each G1 target on the locked
capability fold, then only a survivor may race/gate against `es5_c3g15` under
the T025 fresh full-panel rule.
