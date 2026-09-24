# T015 — Route-table audit per shop pair (owner: codex, from claude 2026-09-24 03:50)
Horizon picks a full legal tape at step 144 from the first two shops (`_router`, agents/horizon_v5_market.py:973; tables `_R108_SHOP_ROUTES`, `_R110_OLD_SHOPS`, `_V92_TABLE`, endgame route 2 from step 648). Swapping the route for a shop pair is a clean knob: every route is an existing legal tape, no new unit scheduling needed.
Evidence to start from:
- Ladder: v5 losses are mostly mirror clones; guarded's recent ones cluster on the sheep route (herd 6/11/0, YARN_STORE worlds) and the Densike −17k loss was SMOOTHIE+YARN. Our ladder episodes with shop pairs: research/census_ours/fp/*.json (`shops`, players' herd), index research/../replays/ours/index.jsonl (sub per episode).
- Opponents that matter (per T004 + tape caveat): v5_market, v4_8turn, yhay_router0913/0909 (clone bases, opponents/pool), parthenos_robust, tschinkel_metav4_v13, tschinkel2945. Tapes = stress only.
Plan: (1) per shop pair, ladder W/L & margin for v5 subs; (2) for weak pairs, try alternative existing routes (all route ids in `_ROUTES`) forced for that pair via seeds whose first two shops match (find seeds by running the env to step 144 — cheap, no agents needed); (3) gate the best per-pair swap on fresh seeds with that pair; (4) only then a combined table. Report paired per-opponent win-rate.

## Execution log

- 2026-09-24 03:xx UTC — Ladder census over `census_ours/fp` (misis player only) identifies `SMOOTHIE_SHOP → YARN_STORE` as the first useful pair: 7 games, 5W/2L but mean margin −1,934. This matches the prior Densike loss note and has enough samples for route screening. Other weak pairs have only 2--5 games and stay descriptive. Next: enumerate the existing route ids and force alternatives only on fresh seeds with this pair.
