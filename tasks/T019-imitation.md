# T019 — Imitation of top-LB algorithms (owner: claude; human asked 2026-09-24)
Replays store every player's full observation (incl. private) per step → we can **teacher-force**: feed a top player's recorded observations to candidate agents and compare with the actions the top player actually took.
Tool: `lab/tools/teacher_force.py` (validated: v5_market on our own ladder episode reproduces 99.86% of recorded actions, first divergence at step 718).
Plan:
1. Ancestry: for top-10 teams × 6 episodes, agreement of 19 candidate "ancestors" (Horizon v3/v4/v4_8/v5, yhay routers 0909/0913, 11 public notebooks) → which public algorithm each top team is built on, and first divergence step. → research/teacher_force_top.jsonl
2. Diff mining vs closest ancestor: at which decisions (op types, days) the top team deviates; categorise (hires, animal buys, planting, sell timing, land).
3. Reconstruct: implement the top team's deviations on top of its ancestor (or on Horizon) → an **imitation agent** of that team → (a) strong reactive opponent for our gate, (b) candidate if it beats es1_g1.
4. BC: (obs, action) pairs at the deviation points → learn the deviation rule (small model / decision tree on obs features) where rules aren't obvious.
- 2026-09-24 ~18:30 — T019 teacher-force run (re)started with fast job listing: 918 jobs (9 teams × 6 eps × 17 agents), 12 workers → research/teacher_force_top.jsonl. Codex T017 PPO runner functional (b9d4d8f), starting training rollouts. ES gen 7 centre 1.046.

## Result of step 1 (2026-09-24 ~19:00, research/teacher_force_top.jsonl, 918 jobs)
**None of our 17 candidate ancestors (Horizon v3/v4/v4_8/v5, yhay 0909/0913, 11 public notebooks) is the ancestor of any top-9 team**: whole-action agreement ≈0, divergence at step 0, farmer-op agreement ≈13% (≈ PASS rate). Tool verified correct (v5 on our own episode: 99.86%). Example DSM (24-0): step 0 BUY_ANIMAL COW + BUY wheat 5; step 1 farmer PICKUP COW, HIRE×4, BUY 1 cow + 3 sheep; step 2 BUILD_PASTURE — an animals-first custom opening, unlike Horizon's wheat trading. ⇒ The top of the LB is custom code; "copy the ancestor + diff" is not available.
## Step 2 (new): behavioural cloning of top teams (Lux-style)
- Data: DSM (16732748) + Mother-Goose (16730612) all active-sub episodes (fetch_team.sh 100/sub, running) + M&M&P&Q (replays/mmpq, 120). Use only the top team's seat; weight wins.
- Model: 10×10 board tensor (tile type/crop/age/water/yield/animal/fed/weed/locked, unit positions + inventories, own vs opp) + global vector (step, day, hour, money, prices, market inventory, shed, seeds, shops, hires_today) → per-unit action head (~45 classes at the unit's cell) + market head (per (op,item) count, ≤10 orders). Train on P40.
- Agent: numpy forward pass embedded in main.py + legality mask from obs; fall back to PASS.
- Eval: teacher-forced accuracy on held-out episodes, then real games vs v5/es1_g1/panel.

## BC log (2026-09-24 evening)
- v1 (mmpq+dsm+mgoose, 180 eps, team-conditioned ResNet 6×96): val unit-action acc **80.4%**, market key acc 96.9%. In real games: **$0–4.5k vs v5's $140–190k** — compounding error: animals escape unfed, weeds, no land. Fixes tried: realistic PICKUP/PLACE quantities, legality masks (seeds/shed/inventory), market affordability → still ~$0–4.5k.
- Diagnosis: moves = 43% of unit actions and only **72.5%** accurate (work ops 86–94%). Wandering units compound.
- v2: added **target-cell head** (per unit, spatial softmax over 100 cells = where the unit does its next non-move action that day) + greedy pathing to it; data grew to 313 eps (DSM 92, Mother-Goose 101, M&M&P&Q 120), 2.3M unit decisions. Training on P40 (~110 s/epoch, 25 epochs). Early: target acc 61% at epoch 0.
- Tools: lab/bc/{feat,build,train,export}.py; numpy agent parity vs torch 1e-5; ~11 ms/forward; BLAS threads limited in-agent.
- **BC v2 final** (25 epochs, 313 eps): val unit acc **82.8%**, target-cell acc **83.8%**, market key acc 97.1%. Real play `runs/bc_v2_final_eval` (8 worlds, both seats, 144 games): **0/144** vs v5_market, boatlee_v16, fukami_v48; margins −135k…−184k. BC alone does not produce a working farm (long production chains break under ~17% per-step error). Next viable path: BC as init + PPO fine-tuning in the exact gpuenv (needs GPU feature extraction; candidate job for the human's 4×H100 box).
## BC → PPO on gpuenv (2026-09-24 night) — lab/bcppo/
- `gpufeat.py`: batched State→features mirror of feat.py; **parity over a full v5-vs-v4 game, both players: max diff 1.2e-7** (parity_test.py). ShopOrder tracks first-two-shop order (State keeps counts only).
- `policy.py`: batched legal masks, target-cell sampling + greedy pathing, op sampling, vectorised prefix-affordability market builder, exact log-prob recompute (first-minibatch |ratio−1| = 1.4e-5).
- Smoke on gpuenv: BC **greedy ≈ $2k (matches official-engine eval), BC sampled ≈ $30k mean, up to $80k** → sampling is a far better starting point than argmax.
- Speed P40: B=1024: net 64 ms, features 16 ms, env step 36 ms per player-step → ~4k game-steps/s. (H100 bf16 should be ≥10×.)
- `ppo.py`: self-play PPO, reward = Δmoney/1e4 dense + 0.5·margin/1e4 terminal, GAE(0.999, 0.95), KL-to-BC anchor annealed. Run r1: 256 envs × 40 iters on P40 → /workspace/shared/bcppo_runs/r1, log runs/bcppo_r1.log.
