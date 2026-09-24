# T020 — Early signal + CMA gate while the human runs pkg v2 on 4×H100 (owner: codex, 2026-09-24 21:10)
1. **Local PPO early-signal run on the P40** (free now), same code as the package: `lab/bcppo/ppo.py` via the package's
   `scripts/ppo_rounds.sh` or directly, config = strong_v2 (init bc_v2 final, team dsm, KL .05 → 0, zero-sum equity reward,
   league snapshot+double), ENVS 128, K 5. Watch money_mean, EV, clipfrac, approx_KL, per-head entropy, executed-op mix,
   seat0/seat1 split. Goal: find training pathologies BEFORE H100 results come back; if you find a bug, fix in lab, tell Claude,
   Claude re-issues a package delta.
2. **CMA-ES gate**: at cma1 gen ≥10, take `runs/cma1/history.json[-1].new_mean_params` → knobs.make_agent_file → h2h vs
   candidates/es1_g9 on 16 fresh non-confirmation worlds both seats (+ v5_market). Promote only if CI > 50% vs g9.
CPU: ≤20 workers (CMA uses 18). Report in inbox/claude.md.

## Started 2026-09-24 21:33 UTC
- P40 diagnostic: package v2 `ppo_rounds.sh`, `strong_v2`, `ENVS=128`, `K=5`, `WARMUP=3`, `KL=0.05→0`, output `h100_pkg/kaggri_bcppo_v2/runs/t020_strong_v2/`.
- CMA gate: frozen completed CMA gen-10 `new_mean_params` copied to `runs/t020_cma_g10/params.json`, agent generated there. 16 fresh seeds excluded from confirmation, development and all CMA-generation seed lists; `compare.py` runs both seats against frozen `candidates/es1_g9/pkg/main.py` and `v5_market`, output `runs/t020_cma_g10/arena/`.

## CMA gate result — gen 10 mean (2026-09-24 22:00 UTC)
- **Do not promote.** Against frozen `es1_g9`: 4–0–28 on 16 fresh worlds × both seats, score 12.5%, whole-world CI [0.0%, 31.25%], mean margin **−$260.56** (CI [−$354.07, −$169.62]), zero errors.
- Context only: versus `v5_market` it is 28–0–4, +$595.13 (CI +$270…+$871), so this CMA centre improved over v5 but is decisively below g9.
- Evidence: `runs/t020_cma_g10/{params.json,seeds.json,arena/}`. P40 strong_v2 diagnostic remains active.

## PPO diagnostic finding — iter 0 (2026-09-24 22:11 UTC)
- Package v2 strong_v2 reached one complete 128-env rollout with no crash, mean terminal cash $88,019 and exactly 64/64 learner seats. But value-only warm-up already produced `approx_kl=0.7531`, `clipfrac=0.6969` (KL-to-BC 0.0658): its value loss traverses the shared policy trunk, so the action distribution moves before PPO is enabled.
- Fixed in lab commit `7c2c1e2` (merged `f5cfdc2`): warm-up updates only `net.value`; all policy/trunk parameters are frozen and restored at the first PPO iteration. A regression update proves every non-value tensor byte-identical. The currently running package is retained as a diagnostic control and is not altered in place.

## P40 control stopped after diagnosis — 2026-09-24 22:18 UTC
- The unpatched package control was deliberately stopped after two complete value-only iterations, rather than consume the P40 while Claude validates the lab fix. Both showed prohibited policy drift: iter0 `approx_kl=.7531`, `clipfrac=.6969`; iter1 `.3124`, `.5780`. No crash, exactly 64/64 learner seats each, but it is invalid as a learning signal.
- Next gate is the separate patched warm-up smoke that Claude has started from lab `f5cfdc2`; do not interpret or resume this old package checkpoint.
