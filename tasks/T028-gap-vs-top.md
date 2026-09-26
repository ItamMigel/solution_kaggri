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

## Follow-up — claimed 2026-09-26 (Codex)

Human requests a bounded post-mortem of the rejected G1 target-5 path on the
locked two-world screen, decomposed against genome0 (goose/coop costs, wheat,
eggs, displaced crop cash and terminal effects).  If its loss is an
implementation leak repairable in under three hours, repair and re-screen;
otherwise start a default-off, route-owned G2 early-tomato timing screen.
Use at most ten workers.  Never submit.

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

## Follow-up result — G1 post-mortem and G2 timing, 2026-09-26 (Codex)

`runs/t028_g1_postmortem_20260926/postmortem_v2.json` replays all 16 locked
G1 screen games with the official miner, pairing target5 with genome0 by
world/opponent/seat.  Target5 has **higher own final cash, +$3,214.5/game**:
egg sales +$8,612.2, offset by milk −$6,672.5, fertilizer sales −$1,280.5,
wheat −$1,220.0, extra wheat purchases +$328.0 and only 28.8 fewer successful
feeds.  Its cash is initially lower (−$2,407 d10, −$1,916 d17), becomes
positive at d24 (+$1,564) and gains a further +$832 in the final day.  So it
is neither a late-placement/idle-goose/wrong-feed failure nor a terminal-only
artifact; its herd trace had already completed with zero mismatches/errors.

The decisive structural loss is the other player in the same worlds: their
final cash rises **+$26,701.5/game** under target5, already +$10,086.5 d17 and
+$20,847.2 d24 (milk +$6,478, among other endogenous sales/shopping effects).
This explains the target5 paired screen margin −$23,487 despite its own cash
gain.  Source rows are not additive because changed actions alter the shared
market/town path.  No sub-three-hour local micro-fix can preserve the G1 herd
while remove that shared-world composition response; G1 remains rejected.

For G2, static inspection of all 41 Horizon route tapes finds **zero native
`PLANT TOMATO` actions**.  The only current plan is dynamic V219: at d18 it
buys SE land + ten tomato seeds and dedicated workers, hence first yield/sale
d26.  The only parent-audited earlier route that fits the tape is
`TomatoInsteadOfCow`: one d0 tomato in the second-cow carrier slot.  Its inner
seed order was overwritten by the final Horizon opening; a default-off G2
wrapper added that single certified spare market order and fails closed if the
three parent opening orders drift.  Official trace: d0 plant, tomato harvests
d8--11, zero mismatch/wrapper errors; genome-off is byte-identical.

That maximum tape-fitting early leg is rejected on a new locked two-world
es5+Parthenos both-seat capability screen (`762192689`, `640729344`): **0/8**,
paired score −0.750 and paired margin **−$4,288.8** (95% world bootstrap
[−$6,651.5, −$1,926.0]), 16/16 DONE.  A larger early crop does not fit the
existing tape: it needs new land/worker movement, which is precisely V219's
d18 route rather than a safe timing knob.  Do not race, gate or create a
candidate.  No Kaggle operation occurred.
