# T043 — es7_wm ladder continuation

Owner: codex. Status: complete. **Kaggle read-only; never submit.**

## Scope

For submissions `es7_wm` (56584540) and `es6_c4g15` (56580877), fetch every
COMPLETED episode ending at or after `2026-09-26T22:00:00Z`, gzip the replay to
`/workspace/shared/replays/ours_final/<submission-id>/`, and report W-D-L,
mean own margin, and the position-based tape-clone/reactive split defined in
`research/ladder_two_classes.md`. Establish whether es7 is climbing from an
API rating trajectory if available, otherwise time buckets. Replay the games
through official-engine hooks to compare own WHEAT `BUY_PRODUCT`/`SELL` volumes
and cash-flow, using the T031 accounting definition.

## Method

Read-only Kaggle CLI/API only; no submission command or mutation. Preserve raw
gzip replays and write a timestamped JSON/Markdown result under
`/workspace/shared/runs/`.

## Result (2026-09-27 08:37Z)

The read-only API returned 54 completed public episodes for `es7_wm` ending
22:07--08:12Z and 51 for `es6_c4g15` ending 22:11--08:18Z. All were fetched
and gzip-preserved in `replays/ours_final/56584540/` and
`replays/ours_final/56580877/` (the directories also retain older snapshots).
Exact included IDs/outcomes, 2-hour buckets, positional-match shares, current
leaderboard rating joins, and accepted official-engine WHEAT commits are in
`runs/t043_ladder_20260927T0835Z/report.json` and `report.md`.

At API time, submissions reported es7 **2058.4** (up from the caller's 1969)
and es6 **2458.8**. The endpoint exposes only the current submission rating,
not a per-episode rating history, so no monotonic rating trajectory is claimed.

| submission | class | n | W-D-L | mean margin | mean current opponent rating |
|---|---|---:|---:|---:|---:|
| es7_wm | all | 54 | 36-0-18 | +$140 | 2089 |
| es7_wm | tape-clone | 51 | 36-0-15 | +$686 | 2081 |
| es7_wm | reactive | 3 | 0-0-3 | −$9,141 | 2224 |
| es6_c4g15 | all | 51 | 26-0-25 | −$1,506 | 2445 |
| es6_c4g15 | tape-clone | 43 | 26-0-17 | −$210 | 2417 |
| es6_c4g15 | reactive | 8 | 0-0-8 | −$8,473 | 2593 |

The 2-hour es7 W-L buckets are 9-1, 8-4, 8-5, 4-4, 7-2, then 0-2 (the last
bucket has only two games). Thus the +89-point current-rating change is upward,
but the observed later record is not evidence of a clean continuing climb.

Replay-exact accepted own WHEAT trade means per game are es7 BUY **303.6** /
$12,025, SELL **518.1** / $20,887, net **+$8,863**; es6 BUY **395.9** /
$15,771, SELL **607.7** / $24,231, net **+$8,459**. So es7 trades about 92
fewer buys and 90 fewer sales but nets **+$404/game** more. Its losses still
have positive WHEAT net cash (+$8,312 versus +$9,138 in wins); all three
reactive losses are +$11,765. This rejects a simple "WHEAT layer is
overtrading/losing cash" explanation, but is not a causal counterfactual and
reactive `n=3` is far too small to clear the barrier.
