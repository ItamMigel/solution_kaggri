# T034 — reactive-class opponents

Owner: codex. Status: closed — research complete, no candidate/gate/submission action. Priority task set 2026-09-26. **Never submit to Kaggle.**

## Goal

The ladder split in `research/ladder_two_classes.md` shows Horizon-family has
only 1–9 against own-route/reactive agents. Obtain a sufficiently broad,
read-only sample of current episodes for fuxi, Joseph Adamski, istinetz and
«Варим сельский самогон», reconstruct daily production/market mechanisms, and
identify a concrete bounded counter-module for es7_wm. Check whether a public
notebook supplies a copyable local stand-in; do not infer source from a replay.

## Method

1. Resolve team IDs and active submissions with the read-only Kaggle CLI, then
   download 30–50 completed episodes per team into
   `/workspace/shared/replays/reactive/<slug>/`, preserving an index with both
   competitors and submission IDs.
2. Re-run episodes with the official local engine and write per-day timelines:
   land unlocks, seasonal hires, herd by species, crop tiles by type,
   fertilizer use, and successful sales (volume/price) per product, for both
   players. Compare reactive player with their episode opponent.
3. Search public Kaggle code read-only for exact team/name/submission evidence.
   Report only source that is directly attributable; otherwise classify it as
   non-copyable from public evidence.

## Result

Read-only fetch completed: 40 recent completed episodes from the two current
active submissions of each requested team (160 total), under
`/workspace/shared/replays/reactive/`. `lab/tools/reactive_census.py`
re-executes official-engine sales/land/hire traces and records each player's
30-day state timeline; tool commit is `9fa7558`.

The reclassified 9 actual own-route losses are fully recorded in
`research/t034_reactive/losses_9.jsonl`; current samples are in
`episodes.jsonl`/`summary.json`. The top defensible mechanisms are (1) third
land d9--10 instead of Horizon d11 (6/9 losses; fuxi/Breaking also fourth
land), (2) a third-land tomato + goose lane rather than fixed late crops, and
(3) better strawberry/milk realized price at lower volume. The last is causal
uncertain and T032 already rejects a narrow advance-only timing gene.

No exact team/member public Kaggle notebook could be attributed to any of the
four, so no strong reactive local stand-in can honestly be copied from source.
Full evidence, caveats, and proposed default-off es7_wm counter-modules are in
`research/reactive_class.md`. No candidate, gate, or Kaggle action is implied.
