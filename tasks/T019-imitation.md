# T019 — Imitation of top-LB algorithms (owner: claude; human asked 2026-09-24)
Replays store every player's full observation (incl. private) per step → we can **teacher-force**: feed a top player's recorded observations to candidate agents and compare with the actions the top player actually took.
Tool: `lab/tools/teacher_force.py` (validated: v5_market on our own ladder episode reproduces 99.86% of recorded actions, first divergence at step 718).
Plan:
1. Ancestry: for top-10 teams × 6 episodes, agreement of 19 candidate "ancestors" (Horizon v3/v4/v4_8/v5, yhay routers 0909/0913, 11 public notebooks) → which public algorithm each top team is built on, and first divergence step. → research/teacher_force_top.jsonl
2. Diff mining vs closest ancestor: at which decisions (op types, days) the top team deviates; categorise (hires, animal buys, planting, sell timing, land).
3. Reconstruct: implement the top team's deviations on top of its ancestor (or on Horizon) → an **imitation agent** of that team → (a) strong reactive opponent for our gate, (b) candidate if it beats es1_g1.
4. BC: (obs, action) pairs at the deviation points → learn the deviation rule (small model / decision tree on obs features) where rules aren't obvious.
- 2026-09-24 ~18:30 — T019 teacher-force run (re)started with fast job listing: 918 jobs (9 teams × 6 eps × 17 agents), 12 workers → research/teacher_force_top.jsonl. Codex T017 PPO runner functional (b9d4d8f), starting training rollouts. ES gen 7 centre 1.046.
