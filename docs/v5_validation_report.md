# Horizon v5 — prepared candidates and validation

Generated 2026-09-23T21:52:49.179304+00:00. **Pre-submission evaluation snapshot.** Both files were subsequently submitted with explicit user authorization and passed Kaggle validation: Market 56504560 and Guarded 56504572. See [submission receipts](../results/round4/v5_submission_summary.json).

## Exact files

| Candidate | Upload-ready archive | Standalone source |
|---|---|---|
| V5 Market | [horizon_v5_market.tar.gz](../submissions/horizon_v5_market.tar.gz) | [horizon_v5_market.py](../agents/horizon_v5_market.py) |
| V5 Guarded | [horizon_v5_guarded.tar.gz](../submissions/horizon_v5_guarded.tar.gz) | [horizon_v5_guarded.py](../agents/horizon_v5_guarded.py) |

The archive contains `main.py`, `LICENSE.txt`, and `NOTICE.txt`. No account, network, external assets, or third-party runtime packages are required by the agents. Preserve their Apache-2.0 notices.

## What changed

Both candidates preserve v4’s production schedules, twelve-turn own-sale advance, late feeding decisions, and last-day collection planner. Both buy eight wheat and sell three at the opening, retaining the same five wheat and one seed while protecting the next day’s worker budget.

Market reapplies the inherited sale-block ordering optimizer after all later layers have finalized the market action. It only rearranges contiguous SELL orders; quantities, worker commands, purchases and hiring barriers remain fixed. It tests order permutations under the inherited model of an opponent with the same planned sales and stock, maximizing the modeled revenue difference. That opponent model is an approximation, not recovered hidden information. The final pass prevents later sale additions from undoing an earlier order optimization. The idea was informed by [Tetsutani’s public notebook](https://www.kaggle.com/code/tetsutani/demand-preserving-turn-sale-timing).

Guarded applies that extra pass only when the opponent’s visible productive farm layout has at least 85% similarity. Empty plots do not create artificial similarity, and at least eight productive positions are required. This is a conservative gate on a clone-based market model; it is not a learned opponent identity.

The expanded replay library, corrected sale estimator, longer advance horizons, and joint worker assignment were evaluated and not included when they failed to improve the wider selection panel. The estimator correction is technically accurate, but the legacy heuristics need joint retuning around the corrected signal. No neural PPO model was trained or deployed in this round.

## Completed evaluation budget

6,784 reacting local games across 232 distinct new world seeds: three selection generations and 3,040 frozen confirmation games across 168 worlds. Both seats were used. All planned games completed, with zero callback failures and unchanged candidate/opponent/harness hashes. The official interpreter was 1.32.7 with natural shop generation.

The seed audit found no overlap between these panels, the 387 world seeds in earlier recorded research plans, or the 95 downloaded public replay worlds. This removes direct world reuse; it does not remove shared policy ancestry.

An additional 8 official file-loader games checked the exact extracted archives and matched the fast interpreter in final rewards, shops, statuses and callback counts (719 per player). These repeated diagnostic worlds are not counted as new independent strength evidence.

Both release sources also passed an isolated `python -I -S` opening callback and recursive import scan using only the standard library. The original research workspace also verified byte-for-byte reconstruction from saved v4; the standalone sources and matching archives are included here.

## Fresh confirmation: ordinary public opponents

64 fresh worlds, six reacting opponents, both seats: 768 games per controller.

| Agent | W / D / L | Score rate | Mean margin | 10th percentile | Worst margin | Losses > 5,000 |
|---|---:|---:|---:|---:|---:|---:|
| Saved v4 | 726 / 0 / 42 | 94.53% | +1309.2 | +180.2 | -1539 | 0 |
| V5 Market | 767 / 0 / 1 | 99.87% | +1669.5 | +586.0 | -1296 | 0 |
| V5 Guarded | 764 / 0 / 4 | 99.48% | +1662.2 | +581.0 | -1296 | 0 |


V5 Market: paired score change +5.34 percentage points; 95% whole-world bootstrap interval [+2.73, +8.59].


V5 Guarded: paired score change +4.95 percentage points; 95% whole-world bootstrap interval [+2.47, +8.20].


V5 Market is the preferred local candidate by the declared win-rate criterion. The guarded gate reduces use of the clone approximation, but this panel does not demonstrate a robustness advantage from it. The candidates share nearly all their code; they are alternatives within one family, not independent strategies.

| Opponent | Saved v4 W / D / L | V5 Market W / D / L | V5 Guarded W / D / L |
|---|---:|---:|---:|
| Thomas / Herd Safe switch | 120 / 0 / 8 | 128 / 0 / 0 | 125 / 0 / 3 |
| Tetsutani sale timing | 120 / 0 / 8 | 128 / 0 / 0 | 128 / 0 / 0 |
| Horizon v3 | 124 / 0 / 4 | 128 / 0 / 0 | 128 / 0 / 0 |
| Idle | 114 / 0 / 14 | 128 / 0 / 0 | 128 / 0 / 0 |
| Meta v4 | 123 / 0 / 5 | 127 / 0 / 1 | 127 / 0 / 1 |
| Wonder | 125 / 0 / 3 | 128 / 0 / 0 | 128 / 0 / 0 |

| Agent | Seat 0 W / D / L | Seat 1 W / D / L |
|---|---:|---:|
| Saved v4 | 365 / 0 / 19 | 361 / 0 / 23 |
| V5 Market | 384 / 0 / 0 | 383 / 0 / 1 |
| V5 Guarded | 383 / 0 / 1 | 381 / 0 / 3 |

## Direct matches against saved v4

64 separate fresh worlds, both seats; 128 games per controller.

| Agent | W / D / L | Mean margin | Median margin | Worst margin |
|---|---:|---:|---:|---:|
| V5 Guarded | 126 / 0 / 2 | +593.8 | +438.5 | -897 |
| V5 Market | 126 / 0 / 2 | +593.8 | +438.5 | -897 |

## Opening attacks: diagnostic stress group

24 separate fresh worlds, both seats; 96 games per controller.

| Agent | W / D / L | Mean margin | Median margin | Worst margin |
|---|---:|---:|---:|---:|
| V5 Guarded | 94 / 0 / 2 | +805.1 | +891.5 | -220 |
| Saved v4 | 8 / 0 / 88 | -20.1 | -17.0 | -1015 |
| V5 Market | 94 / 0 / 2 | +805.1 | +891.5 | -220 |

## Independent-code opponents: weaker stress group

16 separate fresh worlds, both seats; 64 games per controller.

| Agent | W / D / L | Mean margin | Median margin | Worst margin |
|---|---:|---:|---:|---:|
| V5 Guarded | 64 / 0 / 0 | +99416.3 | +95377.0 | +63972 |
| Saved v4 | 64 / 0 / 0 | +99416.3 | +95377.0 | +63972 |
| V5 Market | 64 / 0 / 0 | +99420.8 | +95388.5 | +63972 |

## Runtime and limitations

Maximum measured finalist callback: 234.5 ms in confirmation; 248.8 ms in the official archive-loader diagnostics. Kaggriculture’s nominal action limit is one second. These are local measurements, not a guarantee on every Kaggle host.

Intervals resample complete world blocks containing both seats and all opponents. They condition on this fixed suite; they do not sample unknown future strategies. The public opponents share substantial controller ancestry. The two Lonespear variants form one independent, weaker family. Opening attackers are related stress variants. Their results are reported separately rather than used to inflate the ordinary-opponent score.

A high direct win rate can reflect a small cash advantage, so inspect the direct median margin. All-success bootstrap intervals are degenerate; per-panel scorecards also provide a Wilson lower bound for the fraction of completely won worlds. Identical seeds can produce different future shops when policies change farm occupancy.

**A higher Kaggle rating remains unverified.** Both candidates subsequently passed Kaggle validation at the initial 600 rating; these local tests do not establish ladder strength. The saved v4 remains intact. The latest leaderboard snapshot used in this research was rank 323 / score 2588.0 at 2026-09-23 20:39 UTC.

No finalist exceeded the predeclared ordinary-opponent subgroup regression or severe-loss veto in confirmation.

## Replay evidence and rejected ideas

Read [the research notes](v5_research_notes.md) and [selection ledger](v5_selection_ledger.md) for the friend’s retrospective, six Orbit Wars writeups, papers, public-source provenance and negative experiments.

95 unique public games were downloaded and replayed to their exact recorded final balances. The 79/16 whole-episode library split exported 158 training streams, but teacher overlap and inherited library ancestry remain. Some excluded games were inspected as diagnostics; they are not an untouched generalization test.

Ten of 35 sampled listed losses showed a cash shortage, missed hires, and an escaping cow; none of 24 selected winning controls did. Reproducing all 7,190 original actions across those ten losses and changing only the opening restored the hires and retained the animal every time. Fixed-opponent counterfactual scores were not used for promotion. The integer opening grid tested 14,641 buy/sell combinations per choice: the eight/three opening stayed above the required staffing budget; v4 fell below it in 897 cases.

## What to do next

1. Have the teammate run both candidates against their agent on the unused seeds supplied in the comparison kit. That is more valuable than more tuning against our related public controllers.
2. If new public games become available, prioritize losses against independent production strategies and quantify failed actions, missed revenue and staffing continuity.
3. Retune the corrected sale estimator jointly with market decisions; use whole-episode, teacher and time separation. For neural work, learn feasible production macros before paying for a large PPO run.

## Source and archive fingerprints

V5 Market:

- Source SHA-256: `2038124b9ee04b362ec56511de9e92514c9b0f369c61b019a6178618950e07d4`
- Archive SHA-256: `35307efa84472fe37eb55e75f4d92978d4a5fd44d6572be37fc9761f76349037`

V5 Guarded:

- Source SHA-256: `20f24a06d5eae203b0909dbf31b13ab5c71acb67b0597daea047af55e29d6440`
- Archive SHA-256: `c4dd4b30b5b57ba3adf3e2d0006b95bd62756b5d0a988327927909dd9ab600c2`
