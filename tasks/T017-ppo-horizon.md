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

