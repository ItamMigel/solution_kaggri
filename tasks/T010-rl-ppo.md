# T010 — RL / PPO track (owner: codex)
Direction set by the human 2026-09-23: test RL approaches, esp. what worked in **Orbit Wars** (Kaggle sim comp, finished 2026-07-07, https://www.kaggle.com/competitions/orbit-wars) and PPO.

## Suggested plan (codex decides details)
1. Research (read-only Kaggle): Orbit Wars top write-ups / discussions (`kaggle competitions topics list orbit-wars -s top`, `topics show orbit-wars <id>`), public notebooks. Also kaggriculture RL threads: 741743 (RL → silver), 738619 (PPO to 80k cash), 742246 (neurosymbolic RL), 741730 (self-play), 742737. → `research/rl_orbit_wars.md`: what action abstraction, obs, reward shaping, league/self-play, compute they used, what transfers here.
2. Infra: re-difftest `lab/gpuenv` vs kaggle-environments 1.32.7 (was T006; bit-exact vs OLD engine only; `replay_mine` broke because `_commit_unit` gained `shed_capacity` — expect similar deltas). Old PPO pipeline: `/workspace/kaggriculture/src/rl/` (DESIGN.md, ppo.py, league.py, export.py → numpy main.py). Its lessons: obs encoder had an animal-blindness bug (fixed 08-05); rl6 v3a/v3b checkpoints never confirmed.
3. Most promising framing given 7 days: **residual / control-vector RL on top of Horizon** (policy adjusts a few knobs of the Horizon agent, u=0 = Horizon exactly) rather than from-scratch PPO. From-scratch is fine as a probe if Orbit Wars evidence says so.
4. Gate: `compare.py` vs Horizon v4/v5 + non-Horizon opponents, paired seeds both seats. Anything promising → Claude reproduces before candidates/.
GPU: Tesla P40 24 GB is yours for this track (announce on BOARD). CPU ≤ 22 workers.
