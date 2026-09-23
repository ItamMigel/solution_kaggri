# Round four: evidence and experiment rationale

Prepared without any Kaggle submission or selected-submission change.

## Incumbent and what actually helped

The frozen twelve-turn Horizon v4 is submission 56488922. The leaderboard
download at 2026-09-23 20:39 UTC lists rank 323 and score 2588.0. Ratings are
time-dependent; this is a snapshot, not a promise about subsequent games.
Its source SHA-256 is
`8934ed21b6806556a73f6aeae9ed1a611498ae2abfec13b79b281a0e24ad9483`.

V4 extends v3's **own scheduled-sale horizon** from five to twelve turns. It is
not a twelve-turn full-game search. V3 already included end-of-season feeding,
last-day collection routing, and a refreshed sale-pattern library. The former
2,496-game audit showed twelve turns beating eight and v3 directly, but losing
more often than v3 against some weaker public controllers. The successful live
version therefore supports preserving its production and timing core, not the
claim that deeper timing is universally better. The separate contributions of
v3's three additions were not established by the v4-versus-v3 comparison.

## Friend's retrospective: useful ideas and limits

Source: friend's supplied Russian report (retained in the research workspace). The friend's x612
executable is unavailable, as confirmed by the user. Reported x612 results are
not results measured against our agents.

The most actionable diagnosis is a small opening cash deficit that breaks the
next day's staffing and animal service. We independently found the same pattern
in ten of our 35 listed losses and none of 24 hash-selected winning controls.
These are selected case/control samples, not estimates of the ladder failure
rate. Reproducing all 719 original actions and final balances in each of those
ten games verified the exact submitted controller. Changing only its opening
restored the three hires and retained the fourth animal in all ten cases.
Those changed games use fixed action tapes, so their scores do not establish
performance against a reacting opponent.

The report's failures are also useful: adding workers without a coordinated
production plan, deeper timing tuned on tiny samples, spliced replay routes,
and a restricted-league mixture all failed to generalize in its experiments.
We test coherent changes while preserving the working controller. Evolution
uses shared seeds within each generation and fresh seeds between generations.

## Orbit Wars lessons transferred into this experiment

These are design inferences across different games, not evidence that an Orbit
Wars technique must improve Kaggriculture.

- [First place](https://www.kaggle.com/competitions/orbit-wars/writeups/1st-place-solution-scaling-reinforcement-learnin):
  semantic actions and simulator parity matter. Its large compute budget is
  not available here. The author's discussion of opponent coverage supports
  retaining old champions and explicit exploiters.
- [Second place](https://www.kaggle.com/competitions/orbit-wars/writeups/2nd-place-solution-for-orbit-wars):
  representation and a small effective action set mattered; the final agent
  used RL from scratch despite earlier imitation experiments. This challenges
  the idea that imitation must always precede successful RL. For our project,
  a reliable imitation/evaluation pipeline remains a practical prerequisite.
- [Third place](https://www.kaggle.com/competitions/orbit-wars/writeups/3rd-place-ab-in-den-orbit):
  feasible actions and prioritized historical opponents are useful. We retain
  complete opponents for whole games rather than switching their identity
  mid-episode. This iteration evolves code variants, not neural PPO weights.
- [Fifth place](https://www.kaggle.com/competitions/orbit-wars/writeups/orbit-wars-5th-place-solution):
  imitation, policy anchoring and a historical pool offer a plausible future
  neural pipeline. Our promotion metric remains winning rather than a dense
  cash-profit proxy that might reward exploitable behavior.
- [Eighth place](https://www.kaggle.com/competitions/orbit-wars/writeups/8th-place-how-i-made-ender):
  sequentially update projected resources while constructing joint actions.
  We apply this principle to distinguishing final emitted sales from earlier
  proposals and to preserving market-order feasibility.
- [Eleventh place](https://www.kaggle.com/competitions/orbit-wars/writeups/11th-place-solution-standing-on-the-shoulders-of):
  imitation followed by a league is another successful route, but copying
  actions accurately alone does not prove competitive generalization.

[AlphaStar's league paper](https://storage.googleapis.com/deepmind-media/research/alphastar/AlphaStar_unformatted.pdf)
motivates keeping both historical strategies and targeted exploiters because
pairwise improvements can cycle. Our opening attacker is a stress test with
shared ancestry, not a new independent strategy family.
[Agarwal et al.](https://arxiv.org/abs/2108.13264) motivate reporting uncertainty
and performance distributions. Our intervals resample whole world seeds and
are conditional on the chosen opponent suite.

## New data and what it does not prove

The read-only collection contains 95 unique public episodes: our listed losses,
winning controls, and recent games involving twelve leading teams, deduplicated
before download. All 95 reproduce final balances with the official interpreter.
The library excludes 16 episodes selected by a stable episode hash and exports
158 player streams from the other 79 games. It stores only executed sales,
turns, products, quantities and observed shop context. It never exports replay
seeds, hidden state or the unrevealed shop sequence as policy inputs.

Both seats of an episode stay together. The episode split does not remove
teacher overlap, inherited-library overlap, or chronological dependence.
Some excluded episodes are inspected as diagnostics and therefore are not an
untouched strength holdout. New-library performance must be tested in fresh
reacting games; more replay data is not automatically better.

## New public notebook review

The latest notebook listing was downloaded read-only. Tetsutani's
[Demand-Preserving Turn Sale Timing](https://www.kaggle.com/code/tetsutani/demand-preserving-turn-sale-timing)
reapplies an inherited sale-block optimizer after later action layers. It is a
useful opponent and a structural mutation to test with the opening fix. Its
source and archive hashes match the notebook's declared hashes.
[Statma's Thomas candidate](https://www.kaggle.com/code/statma/kaggriculture-thomas-2944-candidate)
switches between two synchronized public controllers. Its downloaded output
matches its declared source hash. Both opponents share public-controller
ancestry; a number in a notebook title is not verified ladder strength.

[Evgen Dvorkin's replay analysis](https://www.kaggle.com/code/evgendvorkin/kaggriculture)
suggests production and trading ideas, but some interpretations need correction:
the official post-buy quote prevents profit from an isolated unchanged-market
wheat round trip; profit can depend on another player's trades. Our controller
already sells fertilizer and can hire more than six workers. Simply adopting
those recommendations would not be a new improvement. Zeroing cash is unsafe
when it prevents already-planned hires, as our causal audit demonstrates.

## Frozen selection protocol

Generation 1 contains the incumbent and eight variants, 16 worlds, both seats,
four reacting opponents: 1,152 games. It tests two cash-safe opening sizes, final
sale attribution, longer own-sale horizons, confidence filtering, and additional
replay patterns. No candidate or harness changes during a run; no early stop
based on favorable results. Each source, opponent and engine is hashed.

At most three generation-one variants may advance to a fresh 24-world selection
round. Any additional structural mutation is identified as a new experiment,
not silently included in the earlier frozen population. Two final artifacts
require another frozen confirmation panel. Win rates lead selection; per-seat,
per-opponent results, severe losses, lower tails and runtime can veto a choice.
Targeted opening attacks are reported separately from ordinary public opponents.
Reused and inspected panels become development evidence.
