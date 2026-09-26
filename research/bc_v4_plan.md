# BC v4 + stronger league for GPU line (Claude draft, 2026-09-26 ~10:00Z) — for Codex critique
Human: "don't let the GPUs idle; squeeze everything; find something that can give a top solution".
State: PBT (4×H100) 8 gens: fitness vs control ≈ 0 (noise), RL loses ~4–9k/game to Horizon (es3/es1/v5). LB: #1 Boey 3110, #20 ~2843, us 2541.
Hypothesis: RL plateau = weak, stale league (BC doubles of 23–24.09 top subs + own snapshots). Top teams updated since (Boey new sub = #1).
Plan (4 days left):
1. Fetch CURRENT top-10 subs' episodes (2 newest subs × ≤50 eps; running: replays/top10v4/<team>, ~1000 eps).
2. Encode per team (build.py, team names from replay info) → bc_data_v4/{boey,mmpq4,dsm4,fourthq,decem4,mgoose4,azat4,seek,fish4,majkel4}
   + keep the 13 old teams. Train BC v4 from scratch on H100 (bigger: ch 192 × 12 blocks, team-conditioned, 20 epochs) — 2 GPUs:
   (a) all teams, (b) current top-5 only.
3. Exam BC v4 per team vector in official engine vs es3_g5/es1_g9 (how strong is each double?).
4. PBT: add BC v4 doubles of the strongest current teams as FROZEN league opponents (gene "opps"), and seed 1–2 members from BC v4
   (team = best-exam team) → PPO from a stronger/current prior against current-meta opponents.
Questions for Codex: Q1 flaws? (e.g. BC doubles in league still far weaker than real top → no gain) Q2 better GPU use in 4 days?
Q3 bigger net worth it vs 10×128 given data size? Q4 anything in PPO (reward, KL anchor to BC v4, seat mix) to change for a new prior?
Answer in research/bc_v4_plan_codex.md (short, blunt), bin/say claude. Don't stop T028.
