# T041 — top-RE planting throughput

Owner: codex. Status: in progress. Never submit to Kaggle.

## Goal

Address T040’s observed dispatcher failure: while an owned farm has more than ten empty
tiles, a compatible seed and an immediate desired plant target, the globally rematched
units layer emits too few PLANT commands (0.382/turn). Add a bounded, state-only
reservation of plant-capable workers in `lab/re/top_re/units.py`.

## Constraints

- Preserve same-day FEED/WATER emergencies and action legality.
- Do not alter Claude-owned plan/market files or tape agents.
- Compare the bundled agent against frozen `es7_wm` on at least eight fresh seeds in
  both seats, using at most eight workers.
- This is an execution diagnosis only: no candidate, promotion, or Kaggle write.

## Method

First measure the current plant rate and service counts; then make the smallest
reservation change and repeat on the same fresh seed set. Reject the hypothesis if
planting rises only by sacrificing feed/water or if cash/score does not improve.

## Result — rejected (2026-09-26)

Built current `plan_fm` twice: the current Hungarian dispatcher and a bounded
reservation variant (two seed-funded PLANT targets whenever owned empty tiles >10).
Both bundled agents were compiled and compared against frozen `es7_wm` on eight
fresh seeds (`248516905, 1827481004, 649201337, 1974028516, 893716244,
1357019822, 416903755, 209384611`), both seats, eight workers: 32/32 DONE, zero
errors. Both remain 0--16; shared-world mean margin is less negative for reserve
(−$98,282 vs −$108,049), but own cash falls from $49,795 to $45,456 (−$4,339).

A matched 16-game audit confirms the mechanism is adverse: in the 25--40-empty
post-land band, PLANT commands fall **0.351→0.263/turn** while target count falls
7.59→3.99; total PLANT rises only 229.0→232.4/game. FEED falls
**199.7→168.7/game**, CARE 208.3→148.6, and movement rises 43.2→51.2%. This
violates the required service/cash guard, so the units change was reverted.
Artifacts: `runs/t041_plant_throughput/{compare,audit,audit_summary.json}`. No
candidate, promotion, or Kaggle action.
