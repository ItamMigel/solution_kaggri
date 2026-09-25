# BC→PPO v3 — red-team audit Codex (2026-09-25)

Scope: static trace of `/workspace/solution_kaggri/lab/{bcppo/policy.py,bcppo/ppo.py,bcppo/gpufeat.py,bc/export.py,bc/train.py,bc/feat.py}`, plus one bounded P40 rollout micro-profile.  No code was changed and nothing was submitted to Kaggle.

## Q1. Concrete correctness defects / risks

### P0 — PPO likelihood is wrong for a partially truncated repeated market order

**`bcppo/policy.py:197-216`, consumed at `:170-182`.**  `build_market` emits only the first ten order slots, but records the *unclipped* categorical bucket in `mb`.  If, for example, a `BUY_ANIMAL` head sampled 15 when only ten slots remain, the executed action is exactly the same as bucket 10, while `logprob` assigns it probability `P(q=15)`, not `P(q>=10)`.  `minc` excludes a head only when it emitted zero orders; it does not fix this partial-tail case.  Thus the rollout likelihood, PPO ratio and BC KL no longer describe the action that the engine saw.  This is most acute for early ordered keys which consume slots and systematically biases market learning.

**Fix:** make the market decoder sequential/autoregressive with the remaining-slot count in each head's mask; cap each repeated bucket to the remaining capacity before sampling.  If retaining parallel heads, canonicalise an overflowing recorded bucket and use `logsumexp(logits[cap:])` as the likelihood of the final capped bucket (and use the identical aggregation for entropy/KL).  Add an exhaustive unit test over remaining capacity 0…10 and buckets 0…40 that checks equality of both engine action and reported log-probability class.

### P1 — entropy optimises market heads whose sampled choices are guaranteed invisible

**`bcppo/policy.py:177-182`.**  The policy loss correctly gates market log-prob by `rec["minc"]`, but `ent_m` is an ungated sum over every market key.  Fully truncated heads therefore receive entropy gradients despite having no transition effect or likelihood term.  It wastes update budget and makes the reported entropy misleading; together with P0 it may encourage arbitrary high buckets behind the ten-order cap.

**Fix:** multiply per-key market entropy by `minc`, and, after the P0 change, calculate entropy of the same capped/aggregated distribution.  Log `market_visible_keys` and saturation rate.

### P1 — engine has no 16-hand rule; the training/export policy imposes one

**`bcppo/policy.py:146`, `bc/export.py:65,165`, `bc/feat.py:109-120`; engine contract documents this at `gpuenv/spec.md:812,941`.**  `O.MAX_HANDS=16` is a tensor-contract cap, not a Kaggriculture constraint.  The learner masks HIRE at 16 and the export silently does the same.  This is not a current crash, but it is a hard capability ceiling and can become a silent mismatch if the intended teacher/target goes beyond 16 hands.

**Fix:** for v3, at least instrument `n_hands==16` / proposed hires / `State.overflow` and fail evaluation if it fires.  For a real fix, raise the fixed action width and retrain (or implement a separate variable-length hire controller); never claim the current BC can imitate a >16-hand teacher.

### P2 — target-KL is only a post-hoc, noisy statistic, not a guard

**`bcppo/ppo.py:405-434`.**  There is no PPO target-KL early-stop at all.  Further, `mean(old_logp-new_logp)` at `:430` is a Monte-Carlo KL estimate that can be negative and is logged only after applying the update.  This leaves the observed early peak / later collapse unprotected.  `kl_bc` is a different constraint (BC||current), not a trust-region check against rollout policy.

**Fix:** before `opt.step`, compute `log_ratio=new_logp-old_logp`, `approx_kl=((exp(log_ratio)-1)-log_ratio).mean()` (non-negative estimator of KL(old||new)); stop remaining minibatches/epochs when it exceeds 1.5× `--target-kl`.  Save the actual number of updates and max KL.  Start target KL around 0.01–0.02 per rollout, then tune from the 16-world exam rather than money-in-league.

### P2 — the test suite has a blind spot for the stochastic/PPO path

**`bcppo/e2e_test.py:1-4,20-23`; `bc/export.py:179,185`.**  End-to-end parity forces greedy actions, while PPO gathers sampled actions and the exported agent's sampler is a separate NumPy Gumbel implementation.  It therefore cannot catch a sampling/logprob/mask regression such as P0.  Existing greedy e2e parity is still valuable, but insufficient for a PPO release.

**Fix:** add deterministic-uniform/Gumbel injection to both decoders and compare sampled action tensors, recorded masks, `minc`, and log-probs on fixed states.  Also property-test decoder equivalence at cap boundaries (market slots, inventory, seeds, hires).

### Checked items that are *not* a defect in this revision

- `ppo.py:171-191,217-246` correctly presents the learner as player 0, maps actions back, and scores reward/final cash from the learner seat.  Exact half-seat assignment is correct for even batch sizes.
- `ppo.py:239-242` telescopes conservative-equity shaping and restores terminal **cash margin**; it changes only a start-state potential, not the terminal objective.
- `ppo.py:53-64` correctly freezes the shared trunk during value warm-up (the earlier value-only logit drift is addressed).
- `policy.py:80-105` permits movement into LOCKED tiles and masks tile operations there; this agrees with the stated 1.32.7 engine contract.

## Q2. What dominates step time

The draft H1 is correct.  The primary avoidable cost is exactly visible at **`ppo.py:218-222`**: every named league opponent executes `policy.act` on **the full batch** every one of 719 steps, despite each environment drawing only one label.  With five league entries that means six full policy calls (learner + five opponents), then `_merge_actions` discards about five-sixths of the opponent outputs.

There is a second kernel-launch-heavy path in **`policy.py:127-144`**: Python loop over up to 17 units, with nested 5-crop and 12-item loops, clone/mask/scatter/Categorical calls per unit.  This is especially unfriendly to `torch.compile` because `U_eff=int(...)` creates a dynamic host scalar.

Bounded P40 micro-profile (P40 otherwise idle; B=16, 4 timed steps, six calls to the same policy per step, no CPU workers): **policy 433.1 ms/step; gpuenv 176.1 ms/step; policy 71.1%; 26.3 env-steps/s**.  It is not a H100 throughput prediction, but it falsifies any theory that the engine alone is the bottleneck.  The six full forwards dominate before any PPO backward pass.

Priority fixes:

1. Bucket environments by league label and run each opponent only on its selected rows.  Preserve a per-subset `ShopOrder`/state view and scatter actions back; validate byte-identical actions against the current full-batch implementation for a frozen seed.  This is the largest immediate win (near `#league` reduction in opponent work).
2. Make the allocator fixed-width (`for u in range(17)`) and tensorise plant/pickup availability across `U`; then try `torch.compile(mode="max-autotune")`.  Do not compile before removing dynamic `U_eff` and Python-side graph breaks.
3. Use CUDA graphs only after fixed batch/shape and only for stable paths.  A graph cannot repair the redundant 5× opponent forwards.
4. Increase environment count only after (1).  At B=4096, the fp16 board alone is about **17.7 GB** (`719×4096×30×10×10×2`), before `uv`, masks, G, activations and optimizer; it fits 80 GB with care but is not “free”.  B=2048 is the safer first scale point.

## Q3. Is Horizon-double BC sound?

**As data augmentation / a candidate initialisation: yes, conditionally.  As an assumed strong GPU league opponent: no, not until rollout-gated.**  `es3_g5` is a structured tape/replay controller plus repair layers.  On expert trajectories BC can learn its local actions, but a single unit/board action error changes positions and inventory; then the clone visits states absent from the teacher distribution.  The present BC state is also not a full controller state: `gpufeat.py:23-34` retains only whether YARN was among the first two shops, not the full route/tape history.  If es3 decisions distinguish histories collapsed by these features, supervised labels are irreducibly multimodal and high teacher-forced accuracy will overstate closed-loop competence.

Do it, but put hard gates in front of both proposed uses:

1. Generate teacher rollouts over diverse seeds/opponents/both seats, split validation **by whole seed/episode**, and report teacher-forced action accuracy *and* closed-loop cash versus the teacher.
2. Run DAgger: roll out the clone, query es3_g5 on the clone's visited state, append labels.  This directly attacks covariate shift and is much higher value than merely generating more on-policy teacher games.
3. Treat the clone as a league member only after it clears a fixed official-engine competency gate versus es3_g5/g9/v5/panel.  A weak clone teaches PPO to beat an artifact, not Horizon.
4. For initialisation, mix original 13-team BC data with teacher/DAgger data and retain an explicit BC KL floor to the selected mixture.  Do not replace the generalist init wholesale unless its 16-world exam improves.

## Q4. PPO settings for 2048–4096 envs/GPU

The current iteration is already enormous: 512×719 = 368,128 transitions; 4096 is 2.95M.  Keep the number of optimiser updates per rollout roughly stable rather than multiplying it eightfold merely because the batch got bigger.

Suggested first **B=2048** trial (after P0/P1 and subset league work):

- `epochs=1` initially (only move to 2 if target-KL never trips); `mb=65536` (or 32768 if memory requires it), not 8192.
- `lr=5e-6` for first 20–40 iterations; if realised target KL is consistently <0.005, try `1e-5`.  Do not use linear LR scaling with B here.
- `clip=0.10–0.15`, `target_kl=0.01–0.02`, early-stop at 1.5× target, grad norm 0.5–1.0.
- Keep `gamma=1.0`, begin `lambda=.99` (compare `.995` only with fixed exams); preserve exact terminal correction.
- Retain a nonzero BC floor, e.g. `kl_floor=.01–.02` after calibrating the three-head KL scale.  The observed `kl_bc=.28–.44` says the existing `.05` coefficient does not translate to a small policy displacement, so tune from measured action KL rather than coefficient intuition.

For **B=4096**, first increase `mb` to 131072 and/or train in 64–128-step rollout fragments if memory/replay time becomes the bottleneck.  Use B=4096 only if per-GPU throughput keeps improving; otherwise 2048 has better iteration latency and quicker diagnostic feedback.  Four independent single-GPU PPOs are useful for ablations, but they do not create a 4-GPU learner; for one policy, use DDP/all-reduced gradients with fixed per-rank batches and prove resume determinism.

## Q5. Additional ways to squeeze useful signal

1. Promote evaluation quality above raw PPO iterations: fixed 16-world official-engine checkpoint exam, both seats, versus es3_g5/g9/v5 + panel; use paired cash margin and whole-world CI.  Eight games is selection noise, not a checkpoint ranking signal.
2. Record **executed/rejected** unit and market actions from gpuenv, not only requested actions (`ppo.py:455-457` currently logs `None`).  A policy that raises learner money while silently producing invalid actions is not improving control.
3. Make training opponents meaningful before scaling: horizon-double must pass Q3's rollout gate.  Keep snapshots to prevent forgetting, but allocate nontrivial probability to the strongest validated clone rather than a collection of near-identical 95–105k policies.
4. The current 96-channel/6-block ResNet (`bc/train.py:37-43`) is tiny relative to H100.  After throughput is fixed, run one controlled 192/8 or 256/8 BC scaling test, gated on *closed-loop* performance and export latency.  More capacity without DAgger/masks will simply fit teacher-forced data harder.
5. Add state/action coverage reports: market-slot saturation, hand-cap pressure, selected target distance, per-head KL, and teacher disagreement conditional on shop route.  These will distinguish an algorithmic plateau from representational aliasing.

## Bottom line

Do not spend a four-GPU long run before fixing the market likelihood/entropy path and adding PPO target-KL early-stop.  Then implement league subset evaluation, test B=2048 with fewer/larger minibatches and low LR, and gate Horizon-double BC by closed-loop competence—not validation accuracy or its in-league money alone.
