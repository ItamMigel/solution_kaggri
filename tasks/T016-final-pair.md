# T016 — Final-pair confirmation (owner: codex, from claude 2026-09-24 06:50)
Question for the human by 2026-09-28: which 2 submissions should be active at the deadline (currently v5_market + v5_guarded).
Candidates: v5_market, v5_guarded, v4_12turn, v4_8turn (agents/*.py).
Opponents (reactive only — NO frozen tapes, see tape-fragility caveat): yhay_router0913 + yhay_router0909 (ladder clone base), parthenos_robust, tschinkel_metav4_v13, tschinkel2945, ozer_v45, fukami_v48, pilkwang_struct + each candidate vs each other (round robin).
Seeds: `seeds/v5_confirmation.json` (128 worlds, never used for tuning). Freeze the decision rule first via `--decision-note` (e.g. primary = paired score vs clone base + round-robin; tie-break = worst-10% margin).
Also fold in ladder evidence (research/census_ours + ladder_ours.py; T007 notes in tasks/T011-top-games.md). Output: one-paragraph recommendation + table in this file; Claude reviews before it goes to the human.
Budget: ≤22 workers; this is ~4 cand × (8 opp + 3 rr) × 128 × 2 ≈ 11k games → consider 64 worlds first.

## Claude's read of stage 1 (runs/t016_final_pair_64_*/arena, 6144 games, 0 errors) — for codex to confirm/challenge
| cand | score | mean | worst-10% |
|---|---|---|---|
| v5_market | 0.902 | +5669 | −587 |
| v5_guarded | 0.901 | +5661 | −590 |
| v4_12 | 0.771 | +5923 | −1295 |
| v4_8 | 0.702 | +5819 | −2246 |
- v5 beats v4_12 / v4_8 126/128 head-to-head; vs reactive panel v5 ≥ v4 in wins (parthenos 117 vs 105). v4's higher mean margin comes from yhay0913 (+16.3k vs +11.5k), not wins.
- market vs guarded: 5 wins each way, rest draws → near-identical policies; keeping both active wastes a slot.
- Draft recommendation: keep v5 (guarded, the higher-rated one on ladder) + replace the other slot with **es1_g1** if codex's independent reproduction holds (T018: 30-2 vs v5 on fresh worlds).
