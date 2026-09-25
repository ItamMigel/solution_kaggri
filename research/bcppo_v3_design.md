# BC→PPO v3 — squeeze the maximum (Claude draft for Codex audit), 2026-09-25 evening
Human: keep pushing the training, audit the algorithms for bugs and improvement points; H100 run used only ~10 GB / 80 GB per GPU.

## Evidence from H100 run 1 (pkg v2.1, 4×H100, 400 PPO iters/run, ENVS 512)
- BC v3 (13 teams, 10×128): val unit 83.8%, target 84.8%, market non-zero 55.7%.
- PPO money vs league: strong_v2 85→99k, double_dsm 84→99k, double_mmpq 77→94k, strong_v3 98→101k (peak 106k @17!).
  EV≈0.8, clipfrac .14–.24, **kl_bc .28–.44**, 125–136 s/iter, **~10 GB/GPU**, GPU util moderate.
- Official-engine eval (4 worlds×2 seats per ckpt): nothing beats es1_g9/v5/parthenos. strong_v3 best: vs g9 4/8 at it319 (−1.7k), typically −5…−10k;
  others −11…−25k. Our best CPU agent es3_g5 beats g9 32-0 → RL line is still ~5–10k/game behind the Horizon line.

## Diagnosis hypotheses (to confirm/refute)
H1 **Throughput-bound by Python/kernel launches, not GPU**: per step we run policy.act for learner + EVERY league member on the FULL batch
   (5–6 forward passes/step), plus a sequential per-unit Python loop (≤17 iterations × ~20 kernels) per act. → fix: evaluate each opponent only on
   its env subset; vectorise/compile the unit allocator (torch.compile / CUDA graphs); ENVS 2048–4096 per GPU (memory is free).
H2 **Weak training opponents**: the league is BC/PPO lineage only (~95–105k); the target (Horizon line, es3_g5 ~115–150k) is never seen in training.
   → **Horizon double via BC**: generate thousands of es3_g5 games on CPU (48 cores ≈ 3 games/s), BC a GPU policy on es3_g5's decisions (unlimited,
   deterministic teacher, same feature/action space) → (a) strong league opponent on GPU, (b) alternative init for the learner.
H3 **Too-large policy steps / early peak** (strong_v3 peaks at it 17, KL to BC .43): lr 2e-5 + 2 epochs + KL→0 over 400 iters may overshoot; try lr 5e-6–1e-5,
   KL floor, target-KL early stop per update.
H4 **Evaluation noise**: 8 games per opponent per ckpt can't rank checkpoints (±several k). → EVAL_WORLDS 16 on the H100 box's CPUs, plus a fixed GPU-side
   "exam" vs frozen opponents each round (cheap, 1024 envs).

## Proposed v3 plan
1. Code audit (Codex): policy.py / ppo.py / gpufeat.py / export.py — correctness (masks vs engine, log-prob consistency with bf16, advantage/terminal
   handling, seat mapping, league draw, entropy/KL computations), plus perf profile. List bugs + concrete fixes.
2. Perf (Claude): subset-evaluation of league opponents, compile/vectorise unit allocator, ENVS 2048+; target ≥4× steps/s per GPU.
3. Horizon-double BC (Claude): generator of es3_g5 games (vs mirror/v5/yhay/parthenos, both seats) → BC data "es3" → train on H100 (15 min) →
   add as league opponent (and try as init).
4. PPO v3 runs on 4 GPUs: (a) v3 lineage + Horizon-double in league, (b) init from Horizon-double BC, (c) lower lr + target-KL, (d) best of run-1 continued.
5. Gate: official engine vs es3_g5 / g9 / v5 / panel, 16 worlds.

## Questions for Codex
Q1 bugs you can find (be concrete: file:line, failure, fix). Q2 what dominates step time (profile if you can on P40). Q3 is Horizon-double BC sound
(teacher mismatch: es3_g5 is a tape-replayer + repair layers; will BC of it generalise?) Q4 PPO hyper-params for ENVS 2048–4096. Q5 anything else to
squeeze. Write research/bcppo_v3_design_codex.md, then bin/say claude.
