# BOARD — kaggriculture war room
_Updated: 2026-09-23 23:10 UTC by claude. Deadline 2026-09-30 23:59 UTC (7 days)._

## ☠ Agents never submit. Kaggle = read-only. (see AGENTS.md)

## Current state
- **Active on ladder**: `horizon_v5_market` (56504560), `horizon_v5_guarded` (56504572) — uploaded 2026-09-23 22:0x, ratings still climbing from 600 (1495 / 1737 after ~15 episodes).
- **Previous best on ladder**: `horizon_v4` (56488922) = **2590.4** (~rank 300). Now inactive (only 2 latest subs play).
- Team rank on snapshot 2026-09-23 23:01: 2158 (artifact of fresh v5 ratings, not strength).
- Local evidence: v5_market 767/768 vs 6 public controllers, 126/128 vs v4 — but all opponents share ancestry with Horizon; unknown vs real top (≈3000+).
- Biggest unknown: **what the 2900–3060 agents do differently** and how Horizon loses to them.

## Key findings (newest first; one line each, link the task)
- 2026-09-23 — Codex handshake: protocol/board/inbox read; read-only leaderboard command responds (pipeline exit 0), but `head -3` causes CLI `[Errno 32] Broken pipe` (exit 1 with `pipefail`); use a consumer that drains stdout for robust checks. T001/T003 remain unstarted. [codex]
- 2026-09-23 — Final ranking = single Bradley-Terry tournament over ~2 weeks of post-deadline episodes (topic 731587). [claude]
- 2026-09-23 — Kaggle CLI exposes `team-submissions <teamId>` → any team's active subs → `episodes` → `replay`: we can pull top teams' games directly. `topics list/show` reads discussions. [claude]
- 2026-09-23 — `lab/tools/replay_mine.py` crashes on engine 1.32.7 (`_commit_unit` gained a `shed_capacity` arg). [claude]

## Tasks
| id | owner | status | title |
|---|---|---|---|
| T001 | codex | todo | Port `lab/tools/replay_mine.py` + `replay_report.py` to kaggle-environments 1.32.7; verify on a fresh replay (final cash must match replay rewards exactly) |
| T002 | claude | todo | Top-field census: pull recent episodes of top-30 teams, fingerprint strategies (herd/crops/hands/land/sales timing), compare to Horizon |
| T003 | codex | todo (after T001) | Ladder loss mining: all episodes of our v4/v5 subs → W/L, opponent team, margin; P&L diff of every loss vs the opponent |
| T004 | claude | todo | Discussion + public-notebook digest (esp. 742856, 741743, 738619, 742246, 731215, 734000); extract actionable ideas → `research/discussions.md` |
| T005 | — | backlog | Diverse opponent pool: add non-Horizon strong agents (public notebooks, replay-imitations of top teams) to `compare.py` panels |
| T006 | — | backlog | Re-difftest `lab/gpuenv` against engine 1.32.7 (needed only if we do RL/large search) |
| T007 | claude | ongoing | Monitor ladder ratings of v4/v5; recommend final 2 active submissions to the human by 2026-09-28 |
