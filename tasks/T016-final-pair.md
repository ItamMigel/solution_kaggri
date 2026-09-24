# T016 — Final-pair confirmation (owner: codex, from claude 2026-09-24 06:50)
Question for the human by 2026-09-28: which 2 submissions should be active at the deadline (currently v5_market + v5_guarded).
Candidates: v5_market, v5_guarded, v4_12turn, v4_8turn (agents/*.py).
Opponents (reactive only — NO frozen tapes, see tape-fragility caveat): yhay_router0913 + yhay_router0909 (ladder clone base), parthenos_robust, tschinkel_metav4_v13, tschinkel2945, ozer_v45, fukami_v48, pilkwang_struct + each candidate vs each other (round robin).
Seeds: `seeds/v5_confirmation.json` (128 worlds, never used for tuning). Freeze the decision rule first via `--decision-note` (e.g. primary = paired score vs clone base + round-robin; tie-break = worst-10% margin).
Also fold in ladder evidence (research/census_ours + ladder_ours.py; T007 notes in tasks/T011-top-games.md). Output: one-paragraph recommendation + table in this file; Claude reviews before it goes to the human.
Budget: ≤22 workers; this is ~4 cand × (8 opp + 3 rr) × 128 × 2 ≈ 11k games → consider 64 worlds first.
