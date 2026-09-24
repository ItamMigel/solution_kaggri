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
