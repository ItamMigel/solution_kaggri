# T027 — BC→PPO v3 red-team audit

Owner: codex. Status: in progress. 2026-09-25.

Goal: audit the v3 proposal and policy/PPO/feature/BC-export code for correctness and performance bottlenecks; optionally profile a tiny P40 workload, at no more than four CPU workers.  Report exact file:line, failure and safe fix in `research/bcppo_v3_design_codex.md`; do not change training code or submit to Kaggle.

Method: static trace of feature/action/mask/logprob and rollout/PPO/league paths, then a bounded local profile if the package is runnable.
