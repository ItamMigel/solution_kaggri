# T040 — ladder snapshot and top-RE execution audit

Owner: codex. Status: in progress. Never submit to Kaggle.

## Scope

Read-only snapshot of all completed episodes since 2026-09-26 18:30Z for
`es7_wm` (56584540) and `es6_c4g15` (56580877), storing compressed replays
under `replays/ours_final/<submission>/`.  Classify opponent behaviour by the
share of d9–29 turns whose farmer+hand positions equal ours (tape-clone at
least 50%; otherwise reactive), and report per-class W-L and mean margin with
the current ratings.

Separately audit `lab/re/top_re` execution: at the first land purchase which
creates 25–40 empty tiles, test whether plant targets and seeds exist, whether
the units dispatcher receives and emits executable plant work, and report unit
move share.  Any score conclusion needs at least eight fresh seeds in both
seats for every claimed comparison.  At most eight workers; no Kaggle write.

## Result (2026-09-26 22:0xZ)

Read-only ladder snapshot has 45 completed `es7_wm` and 17 `es6_c4g15`
episodes ending after 18:30Z. Replays are gzip files in
`replays/ours_final/es7_wm/` and `replays/ours_final/es6_c4g15/`; the
reproducible position classifier and outcomes are in
`runs/t040_ladder_snapshot.json`.

| submission | class | n | W-D-L | mean own margin |
|---|---:|---:|---:|---:|
| es7_wm | tape-clone | 44 | 32-0-12 | +$725.93 |
| es7_wm | reactive | 1 | 1-0-0 | +$5,882.00 |
| es6_c4g15 | tape-clone | 14 | 8-0-6 | +$65.79 |
| es6_c4g15 | reactive | 3 | 1-0-2 | +$172.67 |

The rating snapshot taken with the same read-only API was es7 **1968.6** and
es6 **2458.5**.  The reactive samples are too small for an inference.

Top-RE was rebuilt with `TOPRE_PLAN=plan_fm`, the current Hungarian units and
the day-zero harvest fix, then run against frozen es7 on seeds 777--784 in
both seats (16/16 DONE, eight processes): mean own cash $46,692.69 versus
$151,381.75, so mean margin **-$104,689.06** (0--16). This is a diagnosis,
not a candidate comparison.  Mean unit move share is **42.51%**.

The land#2 observation has 25--29 empty cells in all 16 games.  It has only
1--7 desired empty crop cells (mean 4.06) and 0--7 immediately seed-qualified
plant targets (mean 3.69); no immediate PLANT command is emitted because each
worker is elsewhere. Across all 4,891 observations with 25--40 empties, there
are 8.55 immediately seed-qualified plant targets per turn but only 0.382
PLANT commands/turn.  Thus targets are generated and often seed-funded, but
are starved by the globally re-matched service/navigation queue; it is not an
absent-target or all-seeds-missing bug. Raw per-game logs:
`runs/t040_topre_planfm_8x2/`.
