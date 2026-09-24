# T017 — PPO over Horizon (owner: codex; start right after T016 stage 1 finishes)
Human (2026-09-24): "do and improve, don't say it's unrealistic". So RL is back — but on top of Horizon, the only strong base.
Interface: `lab/tools/knobs.py` (branch lab) — 24 numeric Horizon knobs (sale horizons, herd/goose thresholds, clone-race horizons, final-day planner, etc.) that functions read at call time; `make_agent_file(params, out)` appends a `globals().update(...)` to horizon_v5_market. Verified: base params == v5_market exactly (4/4 draws), changed params change play.
Claude runs `lab/tools/knob_es.py` = STATIC knob search (ES, one vector per game) → runs/es1.
Your part = the RL version: a policy that sets knobs **per day from game context** (day, shops unlocked/first pair, own/opponent money, herd, prices, clone-race flag, …):
1. Agent wrapper: at each new day, compute features from obs → policy (tiny numpy MLP or linear, embedded weights) → `globals().update(knobs)`; must stay self-contained/Kaggle-loadable, last callable = agent.
2. Training on the real engine via CPU rollouts (≤20 workers; ~14 s/game/core ⇒ ~5k games/h for you): PPO with Gaussian actions, 30 decisions/episode, reward = terminal paired score + margin/40000 vs a reactive panel (v5_market, yhay0913/0909, parthenos, metav4, t2945 — same as ES). Warm start at the base knobs (u=0 ⇒ v5 exactly).
3. Gate every ~N updates on fresh worlds vs v5_market; log to ledger; post checkpoints on BOARD.
If ES finds a better static vector first, re-centre your policy's mean on it (read runs/es1/state.json → `new_mean_params`).

## Progress — 2026-09-24 12:xx UTC (codex)
- Implemented `lab/tools/ppo_horizon.py`: exports a self-contained daily linear knob policy. It uses eight bounded observable features (step/day, both cash balances, hands, quadrants, shops, shed load, mean price), and updates knobs once per player-day before calling Horizon.
- Added static-anchor support. With `anchor=es1_g1/params.json` and zero weights, the wrapper must be exactly the frozen ES candidate; the template originally read the base embedded in `SPACE`, which was corrected to the selected anchor.
- Official-engine smoke: `runs/t017_anchor_smoke_fix_20260924T1128Z`, seed 1433779137, both seats, vs ES anchor and v5_market: 4/4 DONE, 0 errors; 0/2 draws against the ES anchor (exact equality), 2/2 wins against v5_market (+$251 each), as expected for the static ES anchor. This is only an export-equivalence test, not training evidence.
- Next: collect daily action/observation trajectories from the official engine and implement the clipped Gaussian PPO update, centred on frozen `es1_g1`; keep training and evaluation worlds separate.

## PPO smoke — 2026-09-24 13:xx UTC (codex)
- Added `lab/tools/ppo_game_worker.py` and `train_ppo_horizon.py` (commit `b9d4d8f`). Rollouts use `kaggle_environments.make('kaggriculture').run` directly, one isolated Python process per game. The traceable agent is a callable only locally, so the worker can retrieve its 30 daily Gaussian latent actions and feature vectors; the generated candidate is an ordinary deterministic self-contained `main.py`.
- Training reward is paired against the static ES anchor on the same seed, seat and opponent: `(policy_points-anchor_points) + (policy_margin-anchor_margin)/40000`; the update is clipped Gaussian PPO with MC terminal advantages.
- Smoke `runs/t017_ppo_smoke_fix_20260924T1310Z`: one world, both seats versus v5_market, 4/4 DONE, 60 daily decisions. Initial noisy policy scored 1.0 vs static anchor 1.0 (margins $248 vs $251); one PPO update wrote a deterministic candidate.
- Export smoke `runs/t017_ppo_export_smoke_20260924T1313Z`: 8/8 DONE via `compare.py`; updated candidate drew frozen es1_g1 2/2 exactly and won 2/2 each against v3, v4_12turn and v4_8turn. This is functionality evidence only (one world, not a promotion test).

## First full rollout — 2026-09-24 13:xx UTC (codex)
- `runs/t017_train_g0_20260924T1320Z`: four new training worlds × six reactive opponents × both seats, with a static ES-anchor twin for each policy game: 96/96 DONE, 0 errors, 48 paired episodes and 1,440 daily decisions.
- The exploratory Gaussian behaviour policy had 0.9792 points / +$3,789 mean margin; its static anchor had 1.0000 / +$3,855. Paired terminal reward mean was −0.02249. This is expected behaviour-policy cost at `sigma=0.04`, not an evaluation of the updated deterministic policy. One clipped PPO update was applied.
- Next: held-out new-world arena of the deterministic update versus the frozen ES anchor on the same six-opponent panel. Promote nothing unless this independent panel improves with zero errors.

## Held-out gate g0 — 2026-09-24 13:xx UTC (codex)
- `runs/t017_g0_holdout_20260924T1340Z`: four validation worlds disjoint from training, six reactive opponents, both seats, PPO update and frozen `es1_g1` on every same game: 96/96 DONE, inputs unchanged.
- Both candidates had 43–0–5 (score .8958). PPO mean margin $4,399 vs ES $4,505; paired PPO-minus-ES margin −$106.23, 95% world CI [−$315.25, $0]. It did not establish an improvement and is not a candidate.
- Next: independent, more conservative update (lower learning rate and more training worlds), then another disjoint held-out gate.

## Conservative rollout g1 — 2026-09-24 14:xx UTC (codex)
- `runs/t017_train_g1_20260924T1410Z`: eight disjoint training worlds × six opponents × both seats, 192/192 DONE, 2,880 decision records, no errors; one PPO epoch at learning rate 5e-5.
- The noisy behaviour policy and anchor both scored .98958; mean margins $4,476.51 and $4,485.00 respectively (paired reward −0.000212). This is much less destructive than g0 but remains training evidence only.
- Fresh validation now uses eight separate worlds and the same six-opponent panel.

## Held-out gate g1 — 2026-09-24 14:xx UTC (codex)
- `runs/t017_g1_holdout_20260924T1435Z`: eight worlds disjoint from both g1 training and earlier panels; six reactive opponents, both seats, 192/192 DONE and inputs unchanged.
- PPO and frozen ES are exactly tied: 90–0–6, score .9375, mean margin $4,462.29, paired score and margin gains both exactly zero across all 96 matched games. The lower step kept all daily knob changes below effective discrete/control thresholds: g1 is a functional no-op, not a candidate.
- Next: train an explicitly larger but bounded update, then validate only on fresh worlds; preserve ES as fallback.

## Held-out gate g2 — 2026-09-24 16:xx UTC (codex)
- `runs/t017_g2_holdout_20260924T1630Z`: eight new validation worlds, six reactive opponents, both seats, 192/192 DONE and inputs unchanged.
- PPO and ES both scored 91–0–5 (.94792). PPO mean margin was $4,918.40 vs ES $4,883.63: matched PPO-minus-ES margin +$34.77, but 95% world CI [−$1.83,+$76.02] still includes no effect.
- g2 is therefore not a candidate. The result makes a moderate next update worth testing, while frozen ES remains the policy anchor and fallback.


## Held-out gate g3, re-centred on g9 — 2026-09-24 18:xx UTC (codex)
- Training `runs/t017_train_g3_g9_20260924T1745Z`: 12 disjoint worlds × six reactive opponents × both seats, policy plus static g9 anchor, 288/288 DONE, 4,320 daily decisions, no errors. The noisy exploration policy scored .93056 vs g9 .93750 (training evidence only); deterministic candidate was exported.
- Held-out `runs/t017_g3_g9_holdout_20260924T1835Z`: eight fresh worlds, six predeclared reactive opponents, both seats. All 96 target-panel games per candidate were valid (the harness also ran three default baselines, 288 valid games total). On the target panel g3-minus-g9: score −.01042, 95% whole-world bootstrap CI [−.0625,+.03125]; margin −$17.20, CI [−$59.42,+$41.26].
- g3 does not establish an improvement and is not a candidate. Frozen `candidates/es1_g9` remains the PPO anchor and fallback.
