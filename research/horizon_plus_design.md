# Horizon+ : expand the behaviour space, then evolve it (Claude draft for Codex critique) — 2026-09-24 night
Human: "now we only tune hyper-parameters of one algorithm; give it more actions/capabilities and run evolutionary
algorithms on that". Current best = es1_g9 (v5_market + 24 ES/CMA-tuned knobs; 31-1 vs es1_g1, 64-0 vs v5).

## Evidence for where capability is missing (real ladder games, unit-op shares)
| op | top-5 teams (154 games) | ours (309 games) |
|---|---|---|
| PASS (idle) | **4.0%** | **7.4%** |
| FERTILIZE | **2.9%** | **1.7%** |
| moves N/S/E/W | 42.0% | 42.2% |
| HARVEST / COLLECT_FERT / CARE / FEED | 7.7 / 6.2 / 5.0 / 5.0 | 7.0 / 5.5 / 5.9 / 4.8 |
Earlier: top teams keep 4–6 geese (Horizon mostly 0), land earlier, more strawberry, fertilizer used not sold; clones hire ~3 more
hands on day 29. ⇒ idle unit-turns and fertilizer use are the most direct gaps.

## Proposed capability modules (each = on/off gene + parameters; all default OFF ⇒ genome 0 == es1_g9 exactly)
M1 **In-place idle filler**: if the tape gives a unit PASS (or an action that will no-op) and its CURRENT tile has a productive legal
   op (HARVEST ready, COLLECT_FERTILIZER, CARE, WATER unwatered, FERTILIZE if carrying fertilizer, FEED if carrying wheat) → do it.
   No movement ⇒ tape positions stay aligned. Genes: enable, op priority order/weights, day window.
M2 **Fertilizer carry**: when an idle/near-shed unit is shed-adjacent, PICKUP k fertilizer (gene k, day window, crops) so M1 can
   FERTILIZE strawberries/tomatoes it later stands on. Also gene: fraction of fertilizer NOT sold (keep for use).
M3 **Mid-season labour auction**: reuse the final-day planner's trip/beam machinery (`_fd_route`, value/time^power) on days D1..D2
   (genes) to hire extra hands when a visible trip is worth ≥ ratio×fib cost (genes: day window, ratio, max extra hires, trip depth).
   New hands are outside the tape, so they cannot desync it.
M4 **Layer toggles & switch points**: `_SETTINGS` flags (budget_guard, room_guard, clamp_sells, dead_stock, terminal_liquidation,
   front_run), r4 confidence/track_final, RACE detector on/off, sale-reorder on/off, opening wheat qty, endgame switch step (648),
   FD start step (696).
M5 **Contextual knobs**: 2–3 contexts (clone detected / shop family YARN vs not / behind vs ahead in money at day 10) × a subset of
   the 24 knobs.
M6 (later/risky) **Goose line**: buy geese + build coop + place + daily feed as an extra production line on free tiles (top teams).

## Search
- Mixed genome: continuous knobs + module params (CMA-ES) and discrete toggles/switches (GA or pycma integer_variables).
- Evaluation is the bottleneck (~14 s/game/core): use **racing / successive halving** — evaluate all candidates on 2 worlds,
  keep top half, add worlds, … — and common random worlds per generation. Panel = es1_g9 (mirror!), v5_market, yhay0913,
  parthenos, metav4. Fitness = score vs panel + margin/40000; must beat es1_g9 head-to-head.
- Gate as before: fresh worlds, both seats, h2h CI vs es1_g9 > 50%, panel no regression, independent reproduction.

## Proposed split
Claude: M1, M2, M4 (layer code in a Horizon+ wrapper around horizon_v5_market + knobs), unit tests (genome 0 == es1_g9 byte-for-byte
actions on 2 worlds). Codex: critique + M3 (you know the FD planner best?) + EA infra (mixed genome, racing, contexts M5).

## Questions for Codex
Q1 Which modules would you prioritise / drop, and why? Anything obviously missing (e.g. land-timing gene, seed-mix genes)?
Q2 Risks of desyncing the tape (Horizon replays action tapes with repair layers) — which modules are safe?
Q3 EA design under ~800 games/gen budget: racing parameters, population, how to mix discrete/continuous, how to avoid overfitting
   to the panel/seed noise.
Q4 Should the RL (PPO on gpuenv) instead learn these modules' gates? (Horizon can't run on GPU.)
Answer in research/horizon_plus_design_codex.md, blunt and concrete. Do not stop T020.
