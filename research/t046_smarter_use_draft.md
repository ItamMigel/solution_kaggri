# T046 — smarter training / model / post-processing for Pavel's BC3 (Claude draft for Codex critique), 2026-09-29 20:30Z
Human: "while the old dataset is being shared, research with Codex how else to improve training, the model, and post-processing so that
the model is used more cleverly." Deadline 2026-09-30 23:59 UTC; artefacts to human by ~10:00-12:00Z 30.09.
Context: research/t045_bc_improve_codex.md (your audit), t045_bc_improve_draft.md. Fresh 420 top replays (27-29.09) are downloaded
(research/t045_fresh/replays, 14 subs → m15 team slots, see wt/claude/lab/t045/prep_fresh.sh; NOT yet canonicalised - human paused it).
Tools ready: wt/claude/lab/t045/train3_ft.py (--init, fixed team order, episode split), fix_targets.py (B1; 4.35% move targets change on 1 MG game).
Old dataset + original .pt checkpoints are coming from Pavel. GPU: 4×H100 (human-operated) or Pavel's A100. This box: 48 CPU, 1.5 GB disk free.
Per-step budget: actTimeout 1 s + 60 s bank; current 2-model forward ≈22 ms, bank left 54-57 s at game end.

## A. Post-processing / "use the model smarter" at inference (no retraining)
A1 Team-label ensemble: the net is team-conditioned (15 slots); today we always condition on mgoose_cn. Average (or vote) the
   policies under several strong deterministic labels (mgoose, mgoose2, decem, vadim...) = free ensemble of "styles". Cost ×k forwards.
   Or pick the label per game/state (e.g. by shop set / opponent class), since teams specialise.
A2 Market beam / exact market scorer: the market decoder is autoregressive (≤10 slots). Decode top-K sequences (beam), then score
   each by an exact one-step simulation of our own market execution (prices after each unit, same-turn buy→sell, cash constraints)
   + a value proxy (e.g. inventory at teacher-implied prices) and pick the best; or at least reject sequences that the engine will
   fill at 0 (wasted slots) / that sell below a floor. Risk: value proxy wrong → worse than argmax.
A3 Sequential unit decoding with state update (your A5): apply earlier units' effects (DROP/PLACE to shed, WATER/HARVEST/PLANT/BUILD
   tile state) before masking later units; dedupe identical tile jobs. Pure legality/consistency, keeps BC distribution mostly.
A4 Confidence-gated fallbacks: when the ensemble's top-1 prob is low / members disagree, fall back to a safe scripted rule
   (e.g. HG, fill) or to the member with higher confidence; log disagreement rates first.
A5 Endgame: t718 liquidation (done by you), plus deliver remote cargo in the last hours; last-day sell-order ordering by price impact.
A6 Opponent-aware tweaks: detect tetsu-clone (tape) opponents early and apply market-timing layers only then (WM hurt BC globally, but
   maybe not vs the clones).
A7 Short lookahead with the policy itself as the simulator for our own farm only (opponent ignored except market) at a few key
   decisions (land buy, animal buy, hire) — expensive, needs value.

## B. Training
B1 Fine-tune on fresh data (T045 plan) + boundary-label fix as a separate recipe.
B2 Loss re-weighting: per-head weights (market exact is weakest, 51-62%), focal/label smoothing on rare ops; up-weight rare but
   decisive decisions (land, hire, animal buys, day 7-10 herd states) — the herd collapse needed a script (HG).
B3 Teacher filtering/weighting by teacher strength & result (outcome-weighted, soft); drop stochastic teachers (Boey).
B4 Data augmentation: is there any exact symmetry of the farm (10×10, shed at 4-5,4-5)? Horizontal mirror of board + actions if
   the engine is mirror-symmetric → ×2 data for free. Needs verification.
B5 Distil the ensemble (+HG/fill corrections, +team-label ensemble) into one student with on-policy states (self-play rollouts of
   the ensemble, labels = ensemble+HG decisions) → DAgger-style "repair distillation": trains the model on its OWN visited states,
   fixing compounding error. Uses our CPU to generate rollouts. Could also make inference faster → room for A1/A2.
B6 Auxiliary heads: value (final margin) / next-day money prediction → better representation; later usable for A2/A7 reranking.
B7 Longer context: motion/memory features exist (uext) but unused; market history already 3 lags.
B8 Bigger model / longer training on 4×H100 (current 8×128 ResNet, 16 epochs, val plateau at 14 for single team).

## C. Questions
Q1 Rank A1-A7, B1-B8 by expected gain / hour for tonight; what can be screened cheaply on CPU here (league 16 worlds × 2)?
Q2 A1 team-label ensemble: is it sound? which labels? any evidence in Pavel's results (mix4 under DECEM label 0.75)?
Q3 A2: can we build an exact own-market simulator cheaply from engine code (kaggriculture.py _process_market)? what value proxy?
Q4 B5 on-policy distillation: feasible by morning (rollouts on 48 CPU + H100 train)? expected effect vs plain fresh FT?
Q5 Anything we are missing (e.g. what Snorlax 741743 / other top-team write-ups say about BC→improvement)?
