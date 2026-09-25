# T027 — BC→PPO v3: squeeze the training (claude + codex), 2026-09-25
Design: research/bcppo_v3_design.md; Codex audit: research/bcppo_v3_design_codex.md (pending).
H100 run 1 summary in tasks/T019-imitation.md. Human: GPUs only ~10 GB / 80 GB used.
## Log
- 16:20 Horizon-double data: lab/bc/gen_teacher.py (es3_g5 vs mirror/v5/es2c1/yhay0913/parthenos/metav4, seat alternates) → bc_data/es3, 3000 games running (runs/gen_es3.log).
- 16:25 Codex audit (research/bcppo_v3_design_codex.md): P0 market likelihood wrong under 10-order truncation; P1 market entropy ungated; P2 no target-KL stop;
  perf: policy 71% of step time (6 full-batch forwards/step, 5 wasted on league opponents) + per-unit Python loop; B=4096 fp16 board ≈17.7 GB → start B=2048;
  Horizon-double only after a closed-loop competence gate (DAgger infeasible for a tape agent — note).
## Split (v3)
- claude: P0+P1 (sequential market caps: bucket masked to remaining order slots / hire & land caps; same in numpy export), fixed-width vectorised unit
  allocator, sampled-path parity test (injected uniforms), es3 BC + closed-loop gate, hand-cap instrumentation, package v3.
- codex (ppo.py): P2 target-KL early stop (non-negative estimator, stop at 1.5× target), league opponents evaluated only on their env subset (byte-identical
  actions test), executed/rejected action metrics from gpuenv, B=2048 defaults (epochs 1, mb 65536, lr 5e-6, clip .1–.15, target_kl .015, lambda .99).
- 17:00 P0/P1 done (claude): sequential capped market; rec key mcap; test_market_caps OK; greedy e2e 0 diffs. Codex adapting ppo.py.
