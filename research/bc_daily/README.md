# bc_daily — daily control trajectories from real ladder games (T011, claude)
Built by `lab/tools/bc_daily.py` from `research/census*/fp/*.json` (replays re-simulated exactly with `lab/tools/replay_mine.py`).
- `top.jsonl`: episodes of top-30 LB teams' active subs (both players of each episode, so opponents too).
- `ours.jsonl`: our v3/v4/v4_8turn/v5 ladder episodes.
One row = (episode, player, day) with end-of-day state: hands hired that day, herd per species (animals on tiles),
plants per crop, weeds/empty/locked tiles, unlocked shops, money; plus episode outcome (final, opp_final, margin, won).
Filter the teacher set with e.g. `won and name in TOP_TEAMS`. Rebuild: mine → `python bc_daily.py`.
- Caveat: `hands` = len(farm.hands) at the day-boundary snapshot (step % 24 == 0); use it as a relative signal, cross-check with hire counts in fp `hands_by_day`.
