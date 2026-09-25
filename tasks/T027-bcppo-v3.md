# T027 — BC→PPO v3: squeeze the training (claude + codex), 2026-09-25
Design: research/bcppo_v3_design.md; Codex audit: research/bcppo_v3_design_codex.md (pending).
H100 run 1 summary in tasks/T019-imitation.md. Human: GPUs only ~10 GB / 80 GB used.
## Log
- 16:20 Horizon-double data: lab/bc/gen_teacher.py (es3_g5 vs mirror/v5/es2c1/yhay0913/parthenos/metav4, seat alternates) → bc_data/es3, 3000 games running (runs/gen_es3.log).
- 16:25 Codex audit (research/bcppo_v3_design_codex.md): P0 market likelihood wrong under 10-order truncation; P1 market entropy ungated; P2 no target-KL stop;
  perf: policy 71% of step time (6 full-batch forwards/step, 5 wasted on league opponents) + per-unit Python loop; B=4096 fp16 board ≈17.7 GB → start B=2048;
  Horizon-double only after a closed-loop competence gate (DAgger infeasible for a tape agent — note).
- 17:xx Codex P2 merged to `lab` (`92d6093`, `d48b050`, `bbcf325`): non-negative rollout-policy KL estimator with 1.5× target early stop and v3 defaults; PPO records use P0's `mcap`; each opponent is evaluated only on its assigned league rows, with a CPU greedy parity test against the old full-batch path; logs exact gpuenv same-crop plant rejection and hire-cap overflow signals, plus emitted market order count. Torch tests: target-KL, warm-up, market caps and subset parity pass.
## Split (v3)
- claude: P0+P1 (sequential market caps: bucket masked to remaining order slots / hire & land caps; same in numpy export), fixed-width vectorised unit
  allocator, sampled-path parity test (injected uniforms), es3 BC + closed-loop gate, hand-cap instrumentation, package v3.
- codex (ppo.py): P2 target-KL early stop (non-negative estimator, stop at 1.5× target), league opponents evaluated only on their env subset (byte-identical
  actions test), executed/rejected action metrics from gpuenv, B=2048 defaults (epochs 1, mb 65536, lr 5e-6, clip .1–.15, target_kl .015, lambda .99).
- 17:00 P0/P1 done (claude): sequential capped market; rec key mcap; test_market_caps OK; greedy e2e 0 diffs. Codex adapting ppo.py.
- 17:40 unit allocator vectorised (e2e 0 diffs). **BC es3 (Horizon double)** on 327 es3_g5 games, 6×96, 12 ep: val unit 96.6%, target 96.8%, market-nz 90% (vs 83%/55% for top teams). Closed-loop gate vs es3_g5/v5/yhay (8 worlds) running → runs/bc_es3_closedloop.
