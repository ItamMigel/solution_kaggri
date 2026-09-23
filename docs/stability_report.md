# Horizon v4 stability audit — completed

Completed 2026-09-23T09:55:39.675956+00:00. **Preparation only: nothing was submitted or selected on Kaggle during this audit.**

Completed **2,496 games on 208 distinct world seeds**, using both seats and the natural official interpreter. All games finished without callback failures. Maximum candidate callback time was **439.3 ms** on this local run. Candidate, opponent, harness and required Router asset hashes were checked; prepared agent bytes remain unchanged.

The audit does not establish v4 as a stable general upgrade over v3. Observed public-panel results: Horizon v3 496/512 wins, Horizon v4 · 8 turns 490/512 wins, Horizon v4 · 12 turns 482/512 wins. The public-panel win-rate difference between finalists remains uncertain; the interval spans zero. The twelve-turn version is strong in the direct matchups but has worse public-panel cash margins and lower-tail results. Keep v3 as the reference and retain both v4 variants as matchup alternatives; do not change Kaggle selections automatically. Direct matchups and the broader public panel answer different questions; neither establishes strength against unknown top leaderboard policies.

## Direct comparisons — 128 worlds, 768 games

| Agent / matchup | W–D–L | Worlds | Score rate | Mean margin | Worst 10% mean | Worst margin |
|---|---:|---:|---:|---:|---:|---:|
| Horizon v4 · 12 turns vs Horizon v3 | 252–0–4 | 128 | 98.4% | +1011.1 | +9.3 | -2074 |
| Horizon v4 · 12 turns vs Horizon v4 · 8 turns | 248–0–8 | 128 | 96.9% | +800.4 | -182.7 | -1955 |
| Horizon v4 · 8 turns vs Horizon v3 | 240–0–16 | 128 | 93.8% | +927.6 | -127.7 | -1655 |

These are paired seat orientations, not 768 independent worlds. Cash is supporting evidence; the competition rewards match outcomes.

## Fixed public panel — 64 separate worlds, 1,536 games

| Agent / matchup | W–D–L | Worlds | Score rate | Mean margin | Worst 10% mean | Worst margin |
|---|---:|---:|---:|---:|---:|---:|
| Horizon v3 | 496–0–16 | 64 | 96.9% | +3810.5 | -27.3 | -1966 |
| Horizon v4 · 12 turns | 482–0–30 | 64 | 94.1% | +3536.2 | -309.6 | -3511 |
| Horizon v4 · 8 turns | 490–0–22 | 64 | 95.7% | +3847.1 | -138.2 | -2436 |

The panel contains Meta v4, Idle, Wonder and Shop Router. These have public replay/tape ancestry and must not be counted as four independent strong strategic families.

The win-rate differences versus v3 are uncertain at this sample size: both paired 95% intervals span zero. However, twelve-turn cash margins regressed across this panel, and its worst-decile mean and worst individual margin were worse than v3. This does not prove a universal ordering; it does rule out describing the direct-matchup improvement alone as broad stability evidence.

### Paired changes against Horizon v3

| Candidate | Score-rate change | 95% world-block interval | Mean margin change | 95% world-block interval |
|---|---:|---:|---:|---:|
| Horizon v4 · 12 turns | -2.73 pp | [-6.25, +0.59] pp | -274.23 | [-411.16, -148.49] |
| Horizon v4 · 8 turns | -1.17 pp | [-4.30, +1.56] pp | +36.62 | [-83.77, +153.18] |

Twelve turns minus eight turns on the same public opponents: **-1.56 percentage points**, 95% world-block interval **[-4.30, +1.17]**; paired mean margin change **-310.85**, interval **[-406.06, -219.72]**.

### Every public opponent

| Agent / matchup | W–D–L | Worlds | Score rate | Mean margin | Worst 10% mean | Worst margin |
|---|---:|---:|---:|---:|---:|---:|
| Horizon v3 vs Shop Router | 128–0–0 | 64 | 100.0% | +10652.1 | +3969.2 | +258 |
| Horizon v3 vs Idle | 118–0–10 | 64 | 92.2% | +959.3 | -611.4 | -1966 |
| Horizon v3 vs Meta v4 | 123–0–5 | 64 | 96.1% | +1500.8 | +43.8 | -910 |
| Horizon v3 vs Wonder | 127–0–1 | 64 | 99.2% | +2129.7 | +437.7 | -1401 |
| Horizon v4 · 12 turns vs Shop Router | 127–0–1 | 64 | 99.2% | +9977.1 | +3268.5 | -278 |
| Horizon v4 · 12 turns vs Idle | 108–0–20 | 64 | 84.4% | +841.5 | -899.7 | -3511 |
| Horizon v4 · 12 turns vs Meta v4 | 121–0–7 | 64 | 94.5% | +1291.4 | -268.6 | -1074 |
| Horizon v4 · 12 turns vs Wonder | 126–0–2 | 64 | 98.4% | +2034.9 | +226.5 | -2039 |
| Horizon v4 · 8 turns vs Shop Router | 128–0–0 | 64 | 100.0% | +10331.9 | +3579.6 | +87 |
| Horizon v4 · 8 turns vs Idle | 118–0–10 | 64 | 92.2% | +1192.4 | -671.5 | -2436 |
| Horizon v4 · 8 turns vs Meta v4 | 119–0–9 | 64 | 93.0% | +1603.6 | -255.2 | -955 |
| Horizon v4 · 8 turns vs Wonder | 125–0–3 | 64 | 97.7% | +2260.4 | +240.5 | -2122 |

## Independent implementations — 16 separate worlds, 192 games

| Agent / matchup | W–D–L | Worlds | Score rate | Mean margin | Worst 10% mean | Worst margin |
|---|---:|---:|---:|---:|---:|---:|
| Horizon v3 vs Lonespear Big Herd | 32–0–0 | 16 | 100.0% | +117189.5 | +88274.5 | +80174 |
| Horizon v3 vs Lonespear | 32–0–0 | 16 | 100.0% | +72418.3 | +57472.2 | +55567 |
| Horizon v4 · 12 turns vs Lonespear Big Herd | 32–0–0 | 16 | 100.0% | +116966.2 | +87944.5 | +79740 |
| Horizon v4 · 12 turns vs Lonespear | 32–0–0 | 16 | 100.0% | +71918.2 | +56502.2 | +54546 |
| Horizon v4 · 8 turns vs Lonespear Big Herd | 32–0–0 | 16 | 100.0% | +117154.9 | +88281.5 | +80213 |
| Horizon v4 · 8 turns vs Lonespear | 32–0–0 | 16 | 100.0% | +72163.1 | +57045.0 | +55004 |

Lonespear and Big Herd share an implementation family with each other but are independently implemented from the tape-based main agents. They are weaker stress opponents; easy wins here do not establish top-tier strength.

## Runtime and loss severity

| Panel / agent | Seat 0 score | Seat 1 score | Losses >1,000 | Losses >5,000 | Max callback |
|---|---:|---:|---:|---:|---:|
| pairs / Horizon v4 · 12 turns | 96.9% | 98.4% | 3 | 0 | 241.3 ms |
| pairs / Horizon v4 · 8 turns | 93.0% | 94.5% | 1 | 0 | 207.5 ms |
| field / Horizon v3 | 96.9% | 96.9% | 3 | 0 | 385.4 ms |
| field / Horizon v4 · 12 turns | 93.8% | 94.5% | 8 | 0 | 439.3 ms |
| field / Horizon v4 · 8 turns | 95.7% | 95.7% | 3 | 0 | 333.6 ms |
| independent / Horizon v3 | 100.0% | 100.0% | 0 | 0 | 171.3 ms |
| independent / Horizon v4 · 12 turns | 100.0% | 100.0% | 0 | 0 | 189.3 ms |
| independent / Horizon v4 · 8 turns | 100.0% | 100.0% | 0 | 0 | 180.2 ms |

Complete first-shop strata, worst individual games, score intervals and perfect-world Wilson bounds are in the machine-readable reports. Shop strata are post-hoc diagnostics. Bootstrap intervals condition on this frozen suite; they do not represent uncertainty over future opponent strategies. All-win bootstrap intervals are degenerate, not proof of certainty.

## Actual public game checks

**5,752/5,752 actions matched across eight actual non-self public replays.** Four are v3 losses and four are early v4 wins. Self-validation episodes were excluded using submission IDs. This checks deployed behavior; the selected sample is not an unbiased win-rate estimate.

The public-game snapshot was captured at 2026-09-23T09:22:13.644567+00:00. It is a historical diagnostic snapshot, not a live rating update.

| Replay subset | Games | Games with early animal loss | Early animal losses | Failed placement commands |
|---|---:|---:|---:|---:|
| sampled_losses | 4 | 3 | 3 | 11 |
| sampled_wins | 4 | 0 | 0 | 0 |

The four sampled v3 losses had deficits of 12,833–31,548 coins. Three included loss of the initial cow at step 47; all four attempted to place an animal without the required pasture or carried animal at least once. There were no pre-step-576 FEED attempts without carried wheat in those losses. These observations narrow the investigation to production routes, placement preconditions and acquisition decisions; they do not establish a profitable repair. Deliberate early-cow disposal and late-season animal retirement must not be relabeled bugs without counterfactual evidence.

None of the four sampled winning replays had early animal losses or failed placements. This is useful diagnostic contrast but remains a tiny, selected sample with different opponents. The large real-game loss regimes are poorly represented by the easier local public panel; more clone games cannot resolve that coverage gap.

## Data leakage prevention

The previous builder could rerank existing episodes into different splits when downloads expanded the collection. Existing plans now preserve membership and assignments. Extraction rejects split/configuration drift. Training reads only planned episodes, ignores unrelated cache files, and rejects mismatched split labels, unverified reconstructions or duplicate replay hashes. Eight regression tests passed.

The original dataset remains **36 train / 12 validation / 12 test games**, with no duplicate replay hashes found. Twelve of the seventeen test-team display names also appear in training; ten of eleven test winning-teacher names appear among training winners. Those are name-based proxies, before rating filtering, not stable policy IDs. Whole-game separation therefore does not establish generalization to unseen teachers. No new model was trained or promoted in this audit.

A full load through the corrected training path reproduced the prior cleaned worker datasets exactly in size: **62,443 training / 24,497 validation / 17,675 test examples**, with 212 features. The winning-teacher rating filter retains 28/11/8 episodes respectively; these are subsets of the frozen 36/12/12 episode allocation. This check loaded data only; it did not fit another model.

## Interpretation of the seed advice

The advice to use more games and fresh seeds was retained in AGENTS.md, with qualifications: use the same seeds across candidates inside a comparison; rotate seeds between confirmation rounds; count independent worlds and opponent families; evaluate tails and subgroup regressions; and consume a holdout once it informs selection. More clone games alone cannot resolve strategic overfitting.

The interrupted first attempt is excluded entirely. The original fixed plans were rerun under new filenames because the operating system refused reads of the partial log. No candidates, opponents, seeds or budgets were selected from partial scores. These completed results are now consumed evidence, not an untouched test set for future tuning.

## Prepared artifacts and reproduction

- Reference v3 file: [horizon_v3.tar.gz](../submissions/horizon_v3.tar.gz).
- Twelve-turn file: [horizon_v4.tar.gz](../submissions/horizon_v4.tar.gz).
- Eight-turn file: [horizon_v4_8turn.tar.gz](../submissions/horizon_v4_8turn.tar.gz).
- Compact audit summary: [stability_summary.json](../results/stability_summary.json).
- Evaluation policy: [validation_policy.md](validation_policy.md).

Each archive contains exactly its corresponding main.py. No training data or extra packages are required to run these prepared agents. No competition submission should be performed until the user explicitly lifts the restriction.

This report describes the completed research audit. Its original training tools,
opponent sources and per-game logs belong to the research workspace and are not
included in this portable kit. To run new comparisons with your own agent,
follow [the kit instructions](../README.md); the included runner uses the
official environment in a fresh process per game.

The use of interval estimates and robust aggregates follows the evaluation concerns described by [Agarwal et al.](https://arxiv.org/abs/2108.13264); the Kaggriculture-specific panel and decision rules are our own.
