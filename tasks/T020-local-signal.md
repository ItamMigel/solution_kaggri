# T020 — Early signal + CMA gate while the human runs pkg v2 on 4×H100 (owner: codex, 2026-09-24 21:10)
1. **Local PPO early-signal run on the P40** (free now), same code as the package: `lab/bcppo/ppo.py` via the package's
   `scripts/ppo_rounds.sh` or directly, config = strong_v2 (init bc_v2 final, team dsm, KL .05 → 0, zero-sum equity reward,
   league snapshot+double), ENVS 128, K 5. Watch money_mean, EV, clipfrac, approx_KL, per-head entropy, executed-op mix,
   seat0/seat1 split. Goal: find training pathologies BEFORE H100 results come back; if you find a bug, fix in lab, tell Claude,
   Claude re-issues a package delta.
2. **CMA-ES gate**: at cma1 gen ≥10, take `runs/cma1/history.json[-1].new_mean_params` → knobs.make_agent_file → h2h vs
   candidates/es1_g9 on 16 fresh non-confirmation worlds both seats (+ v5_market). Promote only if CI > 50% vs g9.
CPU: ≤20 workers (CMA uses 18). Report in inbox/claude.md.
