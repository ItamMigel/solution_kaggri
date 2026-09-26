# T028 — Where do top-20 teams earn more than es3_g5? (owner: codex, reviewer: claude) — 2026-09-26
Human: knob tuning won't close a ~300–570 rating gap (LB: #1 Boey 3110, #20 ~2843, es3_g5 2541); top teams have action combos Horizon lacks.
Goal: pick ONE capability module (tape-safe, like M1 COLLECT) with the largest $/game gap, implement, gate (T025 full-panel rule) before 2026-09-29.
Steps
1. Fetch ladder episodes of our active es3_g5 sub 56555111 (lab/tools/fetch_ours.sh / fetch_top.py; Kaggle READ-ONLY) — games vs top-20 teams.
2. For each game: per-player income decomposition by source (crop type, animal product, animal sale, fertilizer, land/hire spending) and by day,
   plus unit-turn usage (idle, moves, harvest…) — use replay_mine/census tooling. Aggregate gap = top − ours, ranked by $.
3. For the top-2 gap sources: concrete mechanism (what action sequence they do, when, under which state), and whether it can be added
   to Horizon without desyncing the tape (new units / idle units / market-only / final-day planner).
4. Write research/gap_vs_top.md with the ranked table + recommended module spec; bin/say claude. Then implement (Horizon+ module gene, default off),
   race vs es5_c3g15 and gate.
Never submit.

## Result — 2026-09-26 (Codex)

Step 1 found no direct cohort: 56555111 has 0/142 completed episode IDs in
common with every current top-20 team's submissions.  `research/gap_vs_top.md`
records the therefore-unpaired, explicitly confounded fallback analysis: 80
recent es3 games vs 19 top-team replays, all re-executed with `replay_mine`
(8 workers, zero errors).  Its largest realised-source gap is eggs +$4,952/game:
top reaches 5.9 geese on d11 vs es3's 2.2, via d6--11 coop/build/place/service;
the recommended new capability is a default-off route-owned early goose
microplan, not a market-only purchase.  It does not repeat the T021/T023/T014
negative modules.  Reported to Claude before implementation.
