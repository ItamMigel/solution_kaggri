# T024 — What beats es1_g1 / es1_g9 on the real ladder? (owner: codex, 2026-09-25)
Our actives: es1_g1 (56522075, ~2650) and es1_g9 (56532237, climbing). Pull ALL their episodes (lab/tools/fetch_team.sh or
fetch_ours-style with sub ids), mine them (lab/tools/census.py + replay_mine), and answer:
1. W/L by opponent family: mirror/clone (same herd/seed profile), other Horizon descendants, genuinely different agents (e.g. top-20 teams).
2. For every loss > $1k: where is the money gap (product × day, hires, land, herd, sell prices) — use replay_report.
3. Which gaps are actionable by a tape-safe module or a knob, which need a new macro. Rank by (frequency × $).
Deliver research/ladder_losses_es1.md + concrete module proposals; screen any proposal with race.py (genome0 = es2_c1).
Kaggle is read-only; never submit.

## Started 2026-09-25
- Claimed by Codex. First pass is an offline census of the already downloaded `replays/ours` data; no Kaggle writes and no concurrent game screen while Claude's 18-worker CMA run is active.
