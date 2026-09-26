# T039 — Crop-mix substitution (redirected from market wrapper)

Owner: codex.  Status: closed (negative screen).  Never submit to Kaggle.

## Redirect (2026-09-26)

The steep-item SELL flow model has no usable signal (strawberry/milk/wool are
within ±0.5pp of the hour baseline; only wheat/fertilizer/egg predict).  Drop
the SELL-filter wrapper; no candidate or Kaggle action.

## New goal

Build default-off `crop_mix` over final `es7_wm`.  It may replace an emitted
tape `PLANT` with a crop selected toward a target mix, while retaining the
worker/tile.  First fixed experiment: cap live STRAWBERRY at about 24 tiles
(tops 21–29; es7 is 33) and use WHEAT instead for own feed.  Before allowing a
replacement, prove seed accounting and the replacement crop's water/harvest
path against the original tape; do not treat an ongoing STRAWBERRY/TOMATO tape
as a finite WHEAT/CARROT path without a concrete compatible service schedule.

## Gate

1. Compile and exact default-off identity audit on two official-engine worlds.
2. Enabled capability screen: two worlds, both seats, versus declared es7_wm
control/opponents (≤6 workers).
3. Only a survivor receives a fresh full-panel gate against `es7_wm`.

## Result — closed at the mandatory screen

### Tape and timing audit

- Every native route has the same 239 tape PLANTs: **12 MELON, 163 WHEAT,
  33 STRAWBERRY, 31 CARROT**.  The 33 strawberries are placed d5--11; this
  is the excess relative to the 21--29 top-team range.
- STRAWBERRY is ongoing while WHEAT is finite.  A raw `PLANT STRAWBERRY` →
  `PLANT WHEAT` edit is therefore invalid: the inherited strawberry service
  tour reaches the same tile again at wheat ages 0--3, and the engine removes
  the short crop at the start of nominal age 4.  `crop_mix` retains that tile,
  redirects surplus future `BUY_SEED STRAWBERRY` to `BUY_SEED WHEAT`, waters
  through the inherited visits, then replaces the final age-3 WATER on the
  **same tile** with HARVEST.  No movement/hire/land action is added.
- On two official-engine audit worlds (seeds `771903, 771904`), default-off
  is **0/1,438 action diffs**, 4/4 DONE.  Enabled performs 9 S→W swaps and 7
  seed redirects/world; all 9 finite wheat tiles are harvested, with zero
  missed service, tile mismatch or exception.  Artifacts:
  `runs/t039_crop_mix/{identity,enabled_audit}.json`.

### Fresh two-world screen — reject

Fresh seeds `181902731,181902732`, both seats vs `parthenos_robust`, with
frozen `es7_wm` control in the same compare invocation and four workers:

| Agent | W-D-L | Mean margin | Errors |
|---|---:|---:|---:|
| `es7_wm` | 4-0-0 | +$371.50 | 0 |
| `crop_mix` | 2-0-2 | −$4,491.50 | 0 |

The changed crop mix also changes the endogenous shop trajectory, so the
automatic seed-keyed “paired” field is not a valid causal paired estimate;
the screen's direct score regression is nevertheless sufficient to reject.
No full-panel gate, candidate, promotion, or Kaggle action.  Source builder:
`lab/hplus/crop_mix.py`; audit: `lab/hplus/crop_mix_audit.py`; screen:
`runs/t039_crop_mix/screen/`.

## Original SELL-wrapper handoff (2026-09-26)

The direct T039 headless request for the SELL wrapper was completed before the
redirect above: `candidates_wip/t039/wrapper_template.py` is an append-only
final layer for the exact frozen `candidates/es7_wm/pkg/main.py`.  Its parent
is therefore the final WHEAT layer, after RACE, V92 queue and final-day
planning.  The only mutation authority removes a row when it is an eligible
steep `SELL` and the advisor returns literal `"hold"`; BUY/HIRE/LAND/WHEAT,
all non-eligible rows, and farmer/hands are passed through unchanged.  It fails
open at `step >= 696` and when free shed space is below 12.

The shipped advisor is a `sell` stub.  An official-engine audit deliberately
set `_FM["enabled"] = True` to exercise that code path, then compared serialized
actions against `es7_wm` at every callback on seeds `1851028621` and
`331157374`: both worlds were `DONE/DONE` (721 callbacks each), with **0 action
differences**, 117/111 eligible parent-sale turns, and zero advisor errors.
One forced-hold structural smoke (seed `1851028621`) completed `DONE/DONE` and
made 372 changes / 598 removals with zero violations: every removal was a
seven-item eligible SELL, no row was added, farmer/hands were unchanged, and
none occurred in the final-day window.  This is a handoff artifact only; the
redirect's no-signal conclusion means it is not a candidate or performance
claim.
