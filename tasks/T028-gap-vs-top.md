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

## G1 capability screen — 2026-09-26 (Codex)

Implemented `lab/hplus/goose_microplan.py`: default-off exact conversion of the
two opening cows into geese (buy/build/pickup/place; no new hand, movement or
market slot). The official trace has 10 rewrites and zero mismatches/errors,
but only reaches two geese: target 4--6 needs a genuinely new route. Fresh
2-world both-seat es5_c3g15+Parthenos screen rejects target-2: paired score
−0.750, margin −$2,581 [−$3,198,−$1,965], 16/16 DONE. Do not race/gate it.
Evidence: `runs/t028_g1c/capability/`.

## G1 targets 4/5/6 implementation audit — 2026-09-26 (Codex)

The rejected two-goose leg above is retained only as a negative result.  G1 was
then rebuilt as the specified default-off route-owned 4/5/6-goose plan on
frozen `candidates/es5_c3g15/pkg/main.py`, retaining its COLLECT layer.  It
rewrites only certified parent BUY/BUILD/PICKUP/PLACE actions; later mismatch
disables its rewrites.  It owns only PASS slots on confirmed G1 sites for
in-place service, and sells EGG only through a parent-existing sale slot.

`runs/t028_g1_ready/identity_trace_audit.json` passes: genome-off is action
byte-identical over 1,438 callbacks on two worlds, while all enabled targets
finish DONE with exact final 4/5/6 geese, all sites confirmed and zero
mismatches/errors.  The locked small capability screen is next.  No candidate
or Kaggle operation occurred.

## G1 targets 4/5/6 capability screen — REJECTED, 2026-09-26 (Codex)

On a separately locked two-world fold (seeds `1900229603`, `1149430256`), all
four agents were evaluated simultaneously versus frozen `es5_c3g15` and
`parthenos_robust`, both seats, eight workers: 32/32 games valid and all
inputs unchanged.  Relative to genome0, each enabled target loses 0.750 paired
score: target 4 is −$18,410.75 (world CI −$25,281.5…−$11,540.0), target 5 is
−$23,487.0 (−$24,647.0…−$22,327.0), and target 6 is −$23,670.25
(−$30,637.0…−$16,703.5).  Evidence: `runs/t028_g1_ready/capability/`.

Thus no target survives the capability screen; do **not** run the T025 fresh
full-panel gate and do not create a candidate.  The result is a production
composition trade-off, not an implementation failure: the identity/trace
audit remains clean.  No Kaggle operation occurred.
