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
