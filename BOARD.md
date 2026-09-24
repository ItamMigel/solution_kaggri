# BOARD — kaggriculture war room
_Updated: 2026-09-23 23:10 UTC by claude. Deadline 2026-09-30 23:59 UTC (7 days)._

## ☠ Agents never submit. Kaggle = read-only. (see AGENTS.md)

## Current state
- **Ratings 2026-09-24 05:27 UTC**: v5_guarded **2640.6**, v5_market 2185.6 (ladder W-L 73-12 / 72-4).
- **Active on ladder**: `horizon_v5_market` (56504560), `horizon_v5_guarded` (56504572) — uploaded 2026-09-23 22:0x, ratings still climbing from 600 (1495 / 1737 after ~15 episodes).
- **Previous best on ladder**: `horizon_v4` (56488922) = **2590.4** (~rank 300). Now inactive (only 2 latest subs play).
- Team rank on snapshot 2026-09-23 23:01: 2158 (artifact of fresh v5 ratings, not strength).
- Local evidence: v5_market 767/768 vs 6 public controllers, 126/128 vs v4 — but all opponents share ancestry with Horizon; unknown vs real top (≈3000+).
- Biggest unknown: **what the 2900–3060 agents do differently** and how Horizon loses to them.

## Key findings (newest first; one line each, link the task)
- 2026-09-24 — Human: keep building/improving, don't write things off as unrealistic. New plan: optimise Horizon itself. `lab/tools/knobs.py` exposes 24 Horizon knobs (base == v5 exactly, verified). Claude: ES (T018). Codex: PPO per-day knob policy (T017). [claude]
- 2026-09-24 — T015 ✗ closed: all 12 alternatives to route 9 for the entire Yarn-shop family fail the predeclared 32-world screen (2,496/2,496, no errors); best r0/r2 are −30.2pp on factual Yarn games. Keep route 9. [codex]
- 2026-09-24 — T015 ✗: on four fresh factual Smoothie→Yarn worlds, legacy route 2 loses to current route 9 (24–8 vs 30–2; paired score −0.188, margin −$392; 64/64 error-free). Keep route 9; first 48-game route-8 screen had zero factual target games and is discarded. [codex]
- 2026-09-24 — Timing is safe on Kaggle: across 221 real episodes (v4, v5×2) our overage pool ends at ≥59.8 s of 60; all DONE. [claude]
- 2026-09-24 — T012 ✗: market-only overlay never fired (Horizon buys all 33 strawberry seeds by d3; condition started d5). Any strawberry/fertilizer change needs unit scheduling. [codex]
- 2026-09-24 — T007 ablation: the v4>v5 panel gap is entirely v5's step-0 opening (v5 minus opening == v4; sale-reorder inert). **However** frozen tapes are broken on foreign seeds (buy 1 quadrant instead of 2; ~38% unit ops rejected), so this is likely a tape/market artifact → panel verdict downgraded to inconclusive; rely on ladder. Tape panel = stress test only, applies to T012 gate too. [claude]
- 2026-09-24 — T007 ⚠: on a top-like panel (M&M&P&Q/Mother-Goose tapes + best public), **v4 beats v5**: 199/216 vs 170/216 wins, worst-10% −6k vs −16k; on opponents not selected against v5 the gap is +5pp [0, +10]. Ablation (v5 opening vs sale-reorder) running. Matters for the final 2 submissions. `runs/t007_panel` [claude]
- 2026-09-24 — T007: v5 on ladder so far: market **51-4**, guarded **50-7** (≈55 games each; ratings 2069 / 2518, climbing). Losses are mostly mirror clones (<1.5k); one real loss vs Densike (#22): our 3rd quadrant ($4k d11) + strawberry glut (avg $72 vs their $110). Real season hires: top-5 293 vs ours 271 (+8%, days 2–15 only). [claude]
- 2026-09-24 — T013 ✗: Horizon chassis driven by a whole M&M&P&Q tape loses **0/192** per variant (−71k…−126k); Horizon's layers are coupled to yhay tapes. Raw mmpq tape: 10-22 vs v5, 0-32 vs v4_8turn. Top tapes = opponents only, not candidates. [claude]
- 2026-09-24 — ⚠ CORRECTION [claude]: census "hands" = hands at the day-boundary snapshot, which is ~always 0 (hands are fired nightly) except the final step 718. So "opponents run 11–13 hands vs our 8–10" was **final-day hands only**, not season labour. Seasonal hires will be re-derived from replay_mine `hires` per day. Herd (cows/sheep/geese) and seed findings stand. Thanks codex.
- 2026-09-24 — T010 gate: legacy residual anchor is unusable as a Horizon candidate: **0/32** vs v4_8turn and v5_market on 8 paired worlds, mean **−144.8k** (no errors; 95% world CI [−166.6k, −123.4k]). Stop long legacy PPO; retain exact gpuenv only to search transferable production controls for T012, then gate in Horizon vs M&M&P&Q tape. `runs/t010_legacy_vs_horizon_8x2_20260924T0055Z/` [codex]
- 2026-09-24 — T011: a frozen action tape from a winning game of **M&M&P&Q (#1 LB)** beats v5_market **8/12** on foreign seeds (mean −1.4k for us) — first local opponent that beats v5. Their edge: land d5/d8 (ours d6/d11), 42 vs 33 straw seeds, fertilizer used on strawberries instead of sold. Other top teams' tapes don't transfer (reactive agents). `opponents/tapes/`, `runs/tapes_dev`. [claude]
- 2026-09-24 — T011/T007: real ladder records (last ≤60 games): **v4_8turn 48-12 (+1.0k)** vs **v4 12-turn 32-28 (−3.1k)**; v5 market/guarded 25-2 each so far (vs low-rated opps while climbing). Big losses always vs opponents with 11–13 hands vs our 8–10. Daily control dataset for RL: `research/bc_daily/`. [claude]
- 2026-09-24 — T010 research: a 7-day raw-action PPO is not credible (Orbit top solution used 15B steps/2,400 B200h; Kaggriculture PPO plateaued around 10k steps/s). Transferable plan: bounded daily residual over Horizon, fixed paired external-opponent gate, terminal margin only; prioritize hands and animal-count knobs. First 32-env residual PPO smoke completed (103 s/update; checkpoint/log under `runs/t010_rl_smoke_20260924T0010Z/`), exposing a CPU Horizon-controller bottleneck to remove before a long GPU run. `research/rl_orbit_wars.md` [codex]
- 2026-09-24 — T011 ladder: v4 went only **32-28 (−3.1k mean)** in its last 60 ladder games; losses of −22..−26k are to same-family agents running MORE hands (11 vs 8) and bigger herds incl. 3–6 geese. Top-5 teams all run ~10 hands, 9–10 cows, 5–8 sheep, 4–6 geese. Horizon's gap = production volume, not sale timing. [claude]
- 2026-09-24 — T010: gpuenv PASS vs kaggle-environments 1.32.7: **12/12** fresh episodes, **8,628** full-state comparisons, zero divergences on CUDA fast path and literal market loop. Ported hinge prices, locked shed-access, town intervals/replacement shops, shedCapacity market purchases. Logs: `runs/t010_gpuenv_20260923T2350Z/`. [codex]
- 2026-09-24 — T011: replay_mine fixed for 1.32.7 (final cash matches replay exactly, 5 s/episode). `lab/tools/fetch_top.py` + `census.py` (mine/report). First 36 top episodes: top teams (M&M&P&Q 12-1, Mother-Goose 21-3) buy **5–7 geese**, ~9 cows, 5–6 sheep, 30–33 strawberry, 44–59 carrot seeds, ~10 hands; our v5 game: 12 cows, 5 sheep, **0 geese**. Early sample, being extended. `research/census/report.md` [claude]
- 2026-09-23 — Codex: по указанию пользователя T001/T003 не начинать; ждём новую общую задачу для декомпозиции с Claude. Cron раз в **30 минут** отправляет проверку в текущий чат (доска/inbox/процессы; без дублирования очереди). [Настройка](research/codex-watchdog.md).
- 2026-09-23 — Codex handshake: protocol/board/inbox read; read-only leaderboard command responds (pipeline exit 0), but `head -3` causes CLI `[Errno 32] Broken pipe` (exit 1 with `pipefail`); use a consumer that drains stdout for robust checks. T001/T003 remain unstarted. [codex]
- 2026-09-23 — Final ranking = single Bradley-Terry tournament over ~2 weeks of post-deadline episodes (topic 731587). [claude]
- 2026-09-23 — Kaggle CLI exposes `team-submissions <teamId>` → any team's active subs → `episodes` → `replay`: we can pull top teams' games directly. `topics list/show` reads discussions. [claude]
- 2026-09-23 — `lab/tools/replay_mine.py` crashes on engine 1.32.7 (`_commit_unit` gained a `shed_capacity` arg). [claude]

## Tasks
_2026-09-23 23:45: human set two directions. T001–T005 folded into T011; T006 into T010._
| id | owner | status | title |
|---|---|---|---|
| T010 | codex | in_progress — GPU P40 claimed | RL/PPO track: Orbit Wars RL write-ups + kaggriculture RL threads → PPO / residual RL on gpuenv (re-difftest vs 1.32.7 first). `tasks/T010-rl-ppo.md` |
| T011 | claude | in_progress | Learn from top players' games: fix replay tooling, top-30 census, extract top tapes/routes, imitation opponents, BC dataset. `tasks/T011-top-games.md` |
| T012 | codex | closed ✗ | Market-only production overlay never fired; deeper unit scheduling required. `tasks/T012-horizon-production.md` |
| T015 | codex | closed ✗ | Legal route-table audit: all alternatives to Yarn family route 9 are worse. `tasks/T015-route-table.md` |
| T017 | codex | todo (after T016 stage 1) | PPO over Horizon: per-day knob policy via `lab/tools/knobs.py`, CPU rollouts on real engine. `tasks/T017-ppo-horizon.md` |
| T018 | claude | in_progress | ES over 24 Horizon knobs (static), real engine, reactive panel, fresh worlds/gen → `runs/es1` |
| T016 | codex | in_progress | Final-pair confirmation for the human: v5/v4 candidates versus reactive opponents only. `tasks/T016-final-pair.md` |
| T013 | claude | closed ✗ | Horizon chassis + M&M&P&Q tape (their production plan + Horizon repair/sale/endgame layers) vs v5_market; `runs/t013_screen` |
| T014 | claude | closed (null) | Final-day labour: lower `_FD_HIRE_RATIO` (1.4→1.0/0.7/0.5) in v5; clones end with 11.4 hands vs our 8.3 in all 55 mirror ladder games. `runs/t014_fdhire` |
| T004 | codex | in_progress | Discussion digest (non-RL threads) → `research/discussions.md` |
| T007 | claude | ongoing (ratings log: research/ladder_ratings.md) | Monitor ladder ratings of v4/v5; recommend final 2 active submissions to the human by 2026-09-28 |
