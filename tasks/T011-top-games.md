# T011 — Learn from top players' games (owner: claude)
Direction set by the human 2026-09-23. We have many top-player replays but not their agents.
Angles: (a) fix replay tooling (ex-T001); (b) census of top-30 teams (ex-T002): fingerprints, what beats Horizon;
(c) Horizon is a tape-replayer with repair layers → extract top players' action streams as new routes / shop-conditional tapes;
(d) replay-imitation opponents (tape + minimal reactivity) for a non-Horizon evaluation panel (ex-T005);
(e) BC dataset export (obs, action) for codex's RL track if useful.

## Log
- 2026-09-24 00:0x — (a) done: replay_mine compat fix (commit f1faf4d on lab). Tools: `fetch_top.py` (top-N teams' active subs → episodes → gz replays + index.jsonl), `fetch_ours.sh` (our v3/v4/v5 episodes), `census.py mine|report`.
- Downloads running in bg: logs `runs/fetch_top.log`, `runs/fetch_ours.log`. Re-run `census.py mine` (incremental) then `report`.
## Next steps (night queue, in order)
1. Full census top-30 vs ours; per-shop-pair breakdown; goose/egg economics (why geese?).
2. Head-to-head: episodes where top teams beat Horizon (ours index ∩ opponent names) → P&L diff day-by-day.
3. Tape extraction: per top team, action streams by shop pair → test as Horizon routes / as replay-imitation opponents in compare.py (T005 panel).
4. BC dataset (obs, action) if Codex asks.
- 2026-09-24 ~00:30 tick — census: 112 top episodes + 85 ours mined (0 errors). Top teams (DSM 24-0, Mother-Goose 22-3, M&M&P&Q 18-6, DECEM 17-11): ~9–10 cows, 5–8 sheep, **4–6 geese**, 30–34 straw seeds, 50–66 carrot seeds, 10–20 tomato, ~10 hands, land d6/d9/d10 (3 extra quadrants in most). Boey (#2 LB) is 1-24 in its current recent episodes → its newest sub is likely a weak experiment; LB score is from the other sub.
- Ours on ladder: **v4 (12-turn) 32-28, mean margin −3.1k**; big losses −22..−26k vs teams of the same notebook family with MORE hands (11 vs 8), +2 cows, +1–2 sheep, +3 geese (eg ep 112608132 vs Yasasvi Josyula: they out-produce us in milk +8k, straw +5k, fert +5k, wool +6k, eggs +4.5k). v4_8turn 19-6, +0.9k (losses are near-mirror clones, <2.3k). → Horizon's weakness is **production volume (hands/animals)**, not sale timing.
- 2026-09-24 ~01:10 tick — census v2 (daily tile census) re-mined: 358 top + 236 ours episodes (1 corrupt replay). `ladder_ours.py` per-sub ladder record:
  | sub | n | W-L | mean margin | median |
  |---|---|---|---|---|
  | v4 (12-turn) | 60 | 32-28 | −3.1k | +0.1k |
  | v4_8turn | 60 | **48-12** | +1.0k | +0.9k |
  | v5_market | 27 | 25-2 | +16.8k | +10.2k (low-rated opps, rating still climbing) |
  | v5_guarded | 27 | 25-2 | +18.4k | +5.0k (same caveat) |
  Every big loss: opponent runs 11–13 hands vs our 8–10. Caveat: v4 was rated higher than v4_8turn → tougher opponents; not a clean A/B.
- BC/RL dataset for codex: `research/bc_daily/{top,ours}.jsonl` (21.5k + 14.2k rows), README there.
- 2026-09-24 ~01:40 — public-notebook opponent pool: `/workspace/shared/opponents/pool/<name>/main.py` (11 working: tschinkel2945, tschinkel_metav4_v13, ozer_v45/v43, fukami_v48, boatlee_v16, parthenos_robust, pilkwang_struct, tetsu_demand, prvsiyan_soil, yaxon_reactive_v5). Smoke: v5_market 44/44 + 4/4 vs v4_8turn; closest parthenos_robust (+0.8k), metav4_v13 (+1.1k). **Public pool is not discriminative** → the ladder threat (more hands/herd) isn't represented.
## Next (claimed): T012 Horizon production-volume probe — override hands target (+2/+3) and herd (+geese, +cows) in horizon_v5_market; gate vs v5_market/v4_8turn + pool on v5_development seeds.
- 2026-09-24 ~02:00 — **Top teams are reactive, not tapes**: within one sub, 6 episodes → 4–6 distinct 144-step openings (Mother-Goose, M&M&P&Q, DSM, DECEM, Vadim). Only Boey is a pure tape (identical opening) — and Boey loses 1-24. So splicing top-team continuations onto a shared opening (yhay-style router) is NOT directly possible.
- yhay81 public tape routers pulled: `opponents/pool/yhay_router0909` (with actions.json) and `yhay_router0913` (self-contained). yhay also published "Replay Public Episode Actions Across Seeds" + "Public Match History Router – Rating 2929" (same idea as ours).
- Built 12 **whole-episode top tapes** (best winning games of top-10 teams, ≤2 per team) as fixed opponents: `/workspace/shared/opponents/tapes/tape_*/main.py`. Running v5_market vs them on v5_development (32 worlds, both seats) → `runs/tapes_dev`. Question: do non-reactive top tapes transfer across seeds and threaten v5?
- 2026-09-24 ~02:40 — partial `runs/tapes_dev` (≈140/832 games): whole-episode top tapes mostly DON'T transfer across seeds (v5 wins +24k…+183k vs DSM/DECEM/Vadim/Mother-Goose/mtmr tapes → those agents are reactive). **Exception: M&M&P&Q (#1 LB)** — `tape_mmpq_26860` beats v5_market 8/12 (v5 mean −1.4k, worst −8.3k), `tape_mmpq_33893` 4/10. A frozen tape of the #1 team is the first local opponent that beats v5.
- Diagnosis seed 1772049822 (`runs/mmpq_debug`, replay 000002; v5 87.0k vs mmpq 95.3k): mmpq buys land earlier (d5/d8 vs our d6/d11), plants 42 straw seeds vs 33 → 314 straw sold vs 249 (+12k), sells only 144 fertilizer vs our 345 (they fertilize strawberries instead), more wheat (529 vs 327), no geese. Similar hands (~10–11 both).
- ⚠ timing: v4_8turn max decision 1000 ms on this loaded box (limit 1 s + 60 s overage pool) — watch on ladder logs.
- Downloading all M&M&P&Q episodes (60/sub) → `replays/mmpq` for a tape bank.
## Next
- T013 idea: **Horizon chassis + M&M&P&Q tapes** (their plan + Horizon's repair/sale/final-day layers). First: pure mmpq tapes vs v4_8turn + public pool to size them; then find mmpq tapes sharing an opening to build a shop-pair router.
- 2026-09-24 ~03:10 — `runs/tapes_dev` complete (832 games, 0 errors; ledger): v5 vs tape_mmpq_26860 **42-22** (+11.4k, worst-10% −10.6k), vs tape_mmpq_33893 46-18; Mother-Goose tapes 53-11 / 57-7; others ≥59-5. Early 8/12 was noise of the first worlds, but mmpq tapes remain the strongest local opponents.
- M&M&P&Q newest sub 56497780 is **60-0** in its last 60 ladder games; older sub 56464621 30-30. Their agent is reactive from step 0 (60 episodes → 23 distinct 24-step openings) → no shared-opening router possible.
- Built `opponents/mmpq_bank/ep*/` (60 winning tapes of 56497780) and screening all vs v5 on 4 worlds × 2 seats → `runs/mmpq_bank_screen`.
- T013 tool ready: `lab/tools/mk_horizon_tape.py` = Horizon v5 chassis with an external tape pinned as route 9001 (optionally keep Horizon endgame route 2 from step 648).
- 2026-09-24 ~03:30 — `runs/mmpq_bank_screen` (488 games, 4 dev worlds × 2 seats): v5 wins 375/480 vs the 60 mmpq tapes. Most dangerous: ep112572059 (v5 2/8, −0.6k), ep112604766, ep112586323, ep112554884 (v5 2/8 each).
- **T013 launched** (`runs/t013_screen`, 768 games, dev seeds 4–19 = not the screening worlds): candidates h572 (Horizon v5 chassis + tape 112572059 pinned all game), h572e (same, Horizon endgame route 2 from step 648), h604 (tape 112604766), tape572 (raw tape) vs v5_market, v4_8turn, mmpq26860, mgoose98862, parthenos, metav4. Files in `/workspace/shared/candidates_wip/`.
- 2026-09-24 ~03:50 — ⚠ hands-snapshot bug (spotted by codex): census 'hands' was final-day only. census v3 adds real hires_by_day; re-mining in bg (6 workers, CPU shared with t013). T012 + T004 handed to codex.
- 2026-09-24 ~04:10 — **T013 NEGATIVE** (`runs/t013_screen`, 768 games, 0 errors, ledger): Horizon chassis + pinned mmpq tape loses 0/192 per variant (mean −71k…−126k), with or without Horizon endgame. The raw tape alone: 10-22 vs v5_market (−10.9k), 0-32 vs v4_8turn (−41k), 16-16 vs another mmpq tape. Horizon's layers are coupled to yhay tapes; grafting a foreign plan is dead. T013 closed. mmpq tapes stay useful as **opponents only**.
- 2026-09-24 ~04:20 — T007: ratings v5_guarded 2517.7, v5_market 2068.8 (4.5 h after upload, still climbing). Re-fetching our episodes (runs/fetch_ours2.log) for v5 loss analysis vs higher-rated opponents.
- 2026-09-24 ~04:40 — census v3 done (hires_by_day). **Season hires: top-5 teams 293 vs ours 271 (+8%)**; gap sits in days 2–15 (top 5.8/day d2–5 vs our 4–5; d12–15 ~11 vs 9.3), equal later. Labour gap is real but modest — early-mid game only.
- Ladder (T007) with fresh episodes: v5_market **51-4** (+9.2k mean, n=55), v5_guarded **50-7** (+9.3k, n=57). All but one loss are near-mirror clones (same herd, −12…−1.4k; −4.5k vs julien gaza). Real loss: **Densike (#22, 2889) −17.4k** (ep112629572, SMOOTHIE+YARN world): we bought a 3rd quadrant SE on d11 for $4k + 257 feed wheat ($9.6k) + 17 sheep; our strawberries sold at avg $72 (246u, $17.6k) vs theirs $110 (185u) → we flooded strawberries into a crashed market; they sold 205 more wheat. Money: we led d10 (17.9k vs 6.5k) but fell behind from d15.
- Check: 3rd quadrant is not a systematic mistake — our ladder games with 3 quadrants vs opp 2: 7-2, +28.9k mean (n=9); 3 vs 3: 35-6 (+0.7k). Densike loss is an outlier, not a pattern.
- 2026-09-24 ~05:10 — T007 panel launched: v5_market / v5_guarded / v4_12 / v4_8 vs 8 top-like opponents (4 hardest mmpq tapes, mmpq26860, mgoose, parthenos, metav4) + v3, dev seeds 20–31, 864 games → runs/t007_panel. Reviewed codex T012 overlay (market-only change can't plant/fertilize; asked for unit-op attribution).
