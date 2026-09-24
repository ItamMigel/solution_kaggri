# BC → PPO design review (Claude draft, for Codex critique) — 2026-09-24

## Goal
Within ~5 days (deadline 2026-09-30 23:59 UTC; final = Bradley-Terry over ~2 weeks of post-deadline episodes),
using the human's 4×H100 offline server (no internet; pip from Artifactory; we ship a zip and get logs/checkpoints back
~once or twice a day), produce:
- (A) the strongest possible agent (must beat es1_g9 = Horizon v5 + ES knobs, our current best, ~2655 on ladder), and
- (B) strong reactive "doubles" of top teams (DSM, M&M&P&Q, Mother-Goose, …) as evaluation opponents — today we have no
  realistic reactive stand-in for the real top (frozen tapes break on foreign seeds; BC plays badly).

## What exists (all verified)
- `lab/gpuenv`: exact batched torch engine (codex difftest vs 1.32.7: 0 divergences). P40: env step 36 ms @B=1024.
- BC data: 313 top-team games (M&M&P&Q 120, DSM 92, Mother-Goose 101), 2.3M unit decisions. Only the top team's seat is used; wins weight 1, losses 0.3.
- BC model v2: ResNet 6×96 on 10×10 board (30 ch) + global vector (70 + team one-hot) → per-unit op head (30 classes: op+item),
  per-unit target-cell head (spatial softmax, "cell of the unit's next non-move action that day"), market head (22 keys × 41 qty buckets).
  Val: unit-op acc 82.8%, target acc 83.8%, market key acc 97.1%.
- Decoding: target≠cell ⇒ greedy step toward target among legal moves (best op-logit); at target ⇒ non-move op; legality masks
  (seeds/shed/inventory/tile); fixed-order market with prefix-affordability. numpy agent == GPU policy exactly (e2e 0 action diffs).
- Play: greedy BC ≈ $2k/game; **sampled BC ≈ $30k mean, up to $80–100k**; top teams earn ~$110k, Horizon v5 ~$150k.
  Failure mode: long production chains break (animals escape unfed, weeds, no land) — compounding error.
- PPO v1 (`lab/bcppo/ppo.py`): self-play (both seats current policy), reward = Δmoney/1e4 dense + 0.5·margin/1e4 terminal,
  GAE(0.999, 0.95), clip 0.2, lr 2e-5, 2 epochs, ent 0.001, KL(BC‖π) 0.05 annealed to 0 over the run, value head fresh.
  P40 run r1 (256 envs): money_mean 29.4k → 32.3k after 18 iters (≈92k×2 samples/iter, ~300 s/iter). Slow but monotone-ish.

## My proposal (to be critiqued)
1. **Data**: pull ALL available episodes of the active subs of the top ~20 LB teams (≈100–200 per sub); build BC data per team.
   Keep only games where the team WON (or weight by margin); also consider the opponent's seat when the opponent is itself top-50.
2. **BC v3**: one team-conditioned net for N teams; bigger (10 blocks × 128 ch); aux value head trained on final margin
   (warm start for PPO critic); label smoothing 0.05; 30–40 epochs on H100; per-team held-out episodes.
3. **PPO v2** per team double (4 GPUs × different teams), init = BC v3:
   - opponent: league = self + frozen snapshots + BC doubles of other teams (sampled), not pure self-play;
   - reward: dense Δmoney + terminal margin (keep), maybe + win bonus;
   - KL-to-BC anchor kept non-zero for "doubles" (style preservation), annealed to 0 for the "strongest" track;
   - ENVS 1024/GPU, bf16, minibatch 8192, 2–4 epochs; checkpoints every 5 iters; periodic official-engine eval.
4. **Eval gate**: official engine vs v5_market, es1_g9, yhay0913, parthenos, and the other doubles; both seats; fresh worlds.

## Open questions for Codex (please answer concretely)
Q1. Is the action factorisation right (target-cell + op, deterministic greedy pathing, market buckets)? Better alternatives
    for the unit policy under PPO (e.g. autoregressive per-unit, including moves in the stochastic choice)?
Q2. Compounding error: anything better than "PPO fixes it"? (e.g. DART-style noise injection when building BC data is
    impossible without an expert; can we use Horizon or the gpuenv as a partial expert? state-reset curriculum from replay states —
    gpuenv can be initialised from a replay's state at step t? would that help PPO learn late-game chains?)
Q3. Reward design & credit assignment over 719 steps: Δmoney punishes investment (animals/land) short-term; better:
    potential-based shaping with an asset valuation (animals, plants, inventory at market value)? gamma/lambda choice?
Q4. Opponent/league design given Horizon cannot run on GPU: self-play only risks collapse into a weird equilibrium; what mix?
    Can the tape routers (yhay 0913/0909 = pure tapes) be run on GPU as fixed opponents (they are just action lists)?
Q5. Hyper-parameters for H100 (ENVS, minibatch, epochs, lr, clip, entropy, KL schedule, value pretraining) and what to
    monitor to catch failure early (KL, entropy collapse, money_mean, win-rate vs frozen BC).
Q6. Time plan: 5 days, human syncs ~1–2×/day. What exactly should run on the 4 GPUs in the first 24 h, what we check,
    and the decision points. Is it realistic for (A) to beat es1_g9? If not, should we point all 4 GPUs at (B)?
Q7. Anything in the current code (policy.py / ppo.py / gpufeat.py / feat.py / build.py) you consider a bug or a risk.
Please write your answer into `research/bcppo_design_codex.md` (numbered to match), be specific and blunt.
