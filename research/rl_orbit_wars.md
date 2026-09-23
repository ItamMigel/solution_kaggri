# T010: RL lessons applied to Kaggriculture

Retrieved 2026-09-24 through the read-only Kaggle CLI. Sources below are
competition discussion topic IDs; no submissions were made.

## Evidence

| Source | What it establishes | Applicability |
|---|---|---|
| Orbit Wars [#724268](https://www.kaggle.com/competitions/orbit-wars/discussion/724268), 1st place | PPO self-play eventually won with a 200M transformer and 15B steps, but required 2,400 B200-hours. The author first changed the action from raw angle to target selection; replay parity and a rewritten fast environment were prerequisite. They later wished for checkpoint-league play. | The compute scale rules out raw-action-from-scratch as the main seven-day bet. Environment parity and a smaller action abstraction transfer directly. |
| Orbit Wars [#723728](https://www.kaggle.com/competitions/orbit-wars/discussion/723728), 2nd place | BC reached top 10, RL finetuning top 5. The final policy reduced each entity to no-op/all-in and short-range target selection, then used 10B self-play steps. | A demonstrator warm-up is useful, but full imitation alone is insufficient. We should accept top-replay BC only for the macro control layer. |
| Orbit Wars [#697725](https://www.kaggle.com/competitions/orbit-wars/discussion/697725) | Fast environment before architecture search; add one architecture delta at a time; feature/action inductive bias matters below massive scale; growing PPO clip fraction warns before instability. | Run small, observable residual experiments, with KL/clip-fraction checks and fixed baselines. |
| Kaggriculture [#741743](https://www.kaggle.com/competitions/kaggriculture/discussion/741743) | Silver-zone PPO used **macro** decisions, BC warm-up, then RL; author reports roughly 300k games. Higher-scoring replay demos helped more. Bank difference was informative early, then final win/loss was added. | Direct support for residual macro control and requesting top-replay macro demonstrations from T011. |
| Kaggriculture [#738619](https://www.kaggle.com/competitions/kaggriculture/discussion/738619) | Full-action PPO at ~10k steps/s reached 80k terminal cash then saturated. A 50/25/25 self-play/active/banked pool and BC traces helped; product-level shaping created a melon farm. The author later moved to an executor-plus-intent hybrid. | Reject raw action space. Use terminal margin first; do not reward product activity. Add fixed external opponents before interpreting self-play gains. |
| Kaggriculture [#742246](https://www.kaggle.com/competitions/kaggriculture/discussion/742246) | Exact routing, legality and marginal-price arithmetic belong in the executor; learned policy should own portfolio, land and liquidation decisions. Fixed strong external opponents stop self-play from masking regressions. | Matches Horizon executor plus a daily residual control vector. |
| Kaggriculture [#741730](https://www.kaggle.com/competitions/kaggriculture/discussion/741730), [#742737](https://www.kaggle.com/competitions/kaggriculture/discussion/742737) | Static-opponent training regressed; self-play was weak against public agents. Reported training ranges are many millions of steps / days on stronger GPUs. | Do not interpret a training return as progress. Use short smoke runs only to verify learning mechanics, followed by a paired external gate. |

## Decision and falsifiable first experiment

Train a small PPO policy once per game day, emitting a bounded residual vector
over Horizon's economic controls. `u=0` must reproduce the Horizon baseline
exactly. The executor keeps legal unit routing and market mechanics. Observation
should include own and opponent portfolio, market inventory/price, unlocked-shop
counts and calendar; training reward is terminal money margin, scaled but not
activity-shaped.

First smoke gate: policy rollout, value loss, KL, entropy and clip fraction must
remain finite; a zero residual rollout must equal Horizon's result for fixed
seeds. A later candidate gate is paired both seats against Horizon v4/v5 and
non-Horizon opponents. If its confidence interval includes no effect, it is not
promoted.

## Local fidelity prerequisite

The fresh 1.32.7 corpus passed CUDA fast path and literal market loop: 12/12
episodes, 8,628 full state comparisons, no divergence. See
`/workspace/shared/runs/t010_gpuenv_20260923T2350Z/`.
