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

## Result — closed 2026-09-25
- Read-only snapshot: 121 g1 and 66 g9 completed episodes were downloaded, fingerprinted and re-simulated. Full evidence: `research/ladder_losses_es1.md`; per-loss replay reports: `runs/t024_replay_reports.txt`.
- G1 was 73–0–48; g9 55–0–11. Repeating losses are macro alternatives — Matt Motoki 3–0 vs g1 and Koba 2–0 vs g9 — whose earlier SW land and late commodity mix cannot be repaired by a tape-safe local operation.
- No `race.py` screen was started: T024 yields no causal tape-safe module. A route-conditioned macro is a future hypothesis only; unconditional earlier land is already rejected.
