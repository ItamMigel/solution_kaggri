# Stability protocol, adopted 2026-09-23

User advice: avoid overfitting to a subsample of games; inspect many games and
change seeds. This is useful, but game count alone is not independent evidence.
Two seats in one world are correlated; thousands of turns in one replay are not
thousands of games; related public policies can repeat the same farm strategy.

Use common random seeds across candidates within a comparison, because giving
each candidate different seeds adds noise. Rotate the seed pool between rounds,
not between contestants. Keep immutable development and confirmation records.
Adaptive parameter search consumes validation information even without training
a neural network. The earlier 4/6/8-world selection rounds, and the 50-world
finalist choice, therefore remain selection evidence, not a permanent test set.

## Frozen v4 stability audit

No agent tuning during this audit. Freeze v3 and the two submitted v4 versions.
Predeclare a 128-world head-to-head panel (768 games), a separate 64-world public
panel (1,536 games; Meta v4, Idle, Wonder, Router), and a separate 16-world
independent-controller panel (192 games; Lonespear and Big Herd). Both seats are
mandatory. These total 2,496 games on 208 distinct new world seeds. Public tape
variants are deliberately reported separately from the weaker independently
implemented controllers. They are not counted as six independent strong
strategy families. All games use natural official game dynamics.

No early stopping on scores. Technical failures invalidate the affected panel
until repaired and rerun under a new recorded run ID. Do not silently drop errors
or overwrite previous results. Candidate, opponent, harness and engine source
hashes accompany each run. Consume the confirmation pool after analysis.

Primary comparisons: each finalist versus v3 on common public opponents and
their direct matchups. Report win/draw/loss counts and 95% world-block bootstrap
intervals, paired changes against v3, worst-opponent results, both seats, 10th
percentile margin, worst-10% mean margin, and losses over 1,000/5,000 coins.
Bootstrap intervals condition on this fixed opponent suite; they do not quantify
uncertainty over unknown future opponents. All-success panels have a degenerate
bootstrap interval; report the Wilson lower bound for the fraction of worlds
with every game won as an additional conservative diagnostic, not a guarantee.
Post-hoc shop strata diagnose weaknesses but do not prove causal effects.

Retain both submitted finalists unless the completed evidence supports changing
that decision. A positive mean cash change alone does not justify promotion if
the win-rate difference is uncertain or lower-tail losses materially worsen.
Any revised policy requires another fresh confirmation pool; failed/weak cases
from this audit may be used for development but not as its sole validation.

## Public matches and learning data

Read live matches in timestamped snapshots, excluding self-validation matches.
Report unique opponents and their strength, not just opening wins against weak
opponents. Download losses plus a time/teacher-balanced sample of wins when
investigating behavior; do not train only on winners or only on our losses and
then evaluate on the same episodes. A replay counterfactual requires a reacting
opponent to support an actual strength claim.

For imitation, group all turns and both players by episode; deduplicate IDs and
content; supplement whole-game splits with teacher/policy and chronological
holdouts. Accuracy of verb/item labels is not full joint-action reproduction.
Public replay ancestry shared with an inherited policy must be disclosed.

The emphasis on interval estimates and robust aggregate metrics is consistent
with Agarwal et al., [Deep RL at the Edge of the Statistical Precipice](https://arxiv.org/abs/2108.13264).
The exact Kaggriculture panel and decision rules above are our protocol, not a
claim made by that paper.
