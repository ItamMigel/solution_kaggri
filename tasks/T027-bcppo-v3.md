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
- 18:10 **BC es3 closed-loop FAIL**: 0/96, −$150–165k (earns ~0) despite 96.6% teacher-forced acc. Replay: diverges at step 3 (hands NORTH instead of PICKUP COW), then off-distribution. Cause: deterministic tape teacher ⇒ near-identical early trajectories ⇒ no state coverage (classic covariate shift). Fix: DART — execute ε-perturbed Horizon actions, label with Horizon's clean action (Horizon is a real oracle with repair layers).
- 18:20 stopped clean es3 gen at 774 games; DART gen launched: 2000 games, eps 0.05/0.1/0.2/0.3, 18 workers → bc_data/es3dart (runs/gen_es3dart.log).
- 18:10 pkg v3 local dry-run (OLD mocked, tiny settings): GPU0 lane BC mix on 2082 eps (13.2M unit decisions, RAM ~14 GB) epoch 0 still running on P40; GPU1-3 lanes fail only with 'No CUDA GPUs' (single-GPU box) — will test those paths on GPU0 after. DART gen 751/2000.
- 18:30 dry-run fixes: exam games hit compare 180 s wall timeout (10×128 numpy ≈93 ms/step; fine for Kaggle's 1 s) → export_eval --game-timeout 900; exam made non-blocking (was '&&' → PPO never started). Testing all 4 lanes sequentially on GPU0 (runs in scratchpad pkg3/lanes.log).
- 18:45 codex watchdog caught duplicate strong_mix (run_all_v3's GPU0 lane had continued: export_eval pipes compare into tail so exam never blocks) + my lanes.sh → killed the run_all one. DART 1201/2000.
- lanes: STRONG_MIX_OK, V3_CONT_OK; v3_fresh + double_es3 pending. DART 1701/2000.
- 19:00 **pkg v3 READY**: h100_pkg/kaggri_bcppo_v3.zip (427 MB, sha256 61fc85dd…), all 4 lanes passed tiny dry-run, DART 2000 games included. Local check started: BC es3+es3dart (6×96, 10 ep) → closed-loop exam (runs/bc_es3dart_v1.log).
- 20:20 H100 v3: ENVS 6256 → ~26k steps/s/GPU (174 s/iter for 4.5M samples), value warm-up EV .54; OOM at first policy update with MB 65536 on 10×128 → human told MB=16384 + expandable_segments; package defaults updated. BC es3+DART (6×96, 10 ep): val unit 88.4%, target 88.0%, market-nz 92% → closed-loop exam running (runs/bc_es3dart_closedloop). Codex gen-15 gate was vs es2_c1 (+$94) — asked to gate vs es3_g5.
- 20:45 **BC es3+DART closed-loop FAIL too** (0/96, −139…−165k) despite val 88%/92% → Horizon's decisions depend on hidden tape/route state not in features; Horizon-double track closed. H100: repurpose GPU3, run strong_mix PPO with team dsm.

## 2026-09-25 23:05Z — PBT (Claude, human request: "all GPUs on the strongest line, evolve it")
H100 run v3: v3_cont 98k→109k league money (best @32, EV .98) = best RL line; strong_mix/double_es3 dead (es3dart vector).
Built PBT in the package: 4 members from one START ckpt (v3_cont best), league = each other + frozen BC team doubles,
CPU controller exams newest roundNNN of all members in official engine vs es3_g5/es1_g9/v5 (6 rotating worlds),
worst ← best weights + mutated genome {lr, ent, clip, epochs, kl_floor, target_kl, team (teacher style), opps}.
Codex review fixed 7 issues (research/pbt_codex.md). Smoke on P40 running (scratchpad/pbttest). Then zip + launch cmd for human.
- 23:00Z PBT exam auto-scales to CPU: workers = nproc − OMP×members − 8 (H100 box 128 cpu → ~104), worlds 12 if nproc≥96.
  Smoke on P40 slow (~20+ min/iter at 48 envs, 2 members sharing GPU; earlier 8-env iter was 635 s) — waiting for first round→exam→exploit.
- 23:35Z PBT smoke (P40, 2 members, 8 envs, K=1, 1 world) passed the full loop: round → publish roundNNN → official exam (+ start control)
  → EXPLOIT (worst ← best weights, Adam/RNG reset, mutated hp) → next round; hall of fame + tar written.
  Found: exam worlds rotate and opponents score 94k on one world vs 162k on another → fitness now RELATIVE to the start control
  evaluated every generation on the same worlds (smoothing/hall-of-fame were comparing different worlds). nproc bug (obeys OMP_NUM_THREADS)
  fixed; CPU = min(nproc, cgroup quota). Human's box: 224 visible / 128 quota → ~104 exam workers, 12 worlds.
