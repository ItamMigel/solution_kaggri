# T044 — Tetsutani market-edge attribution

Owner: codex. Started 2026-09-28 21:46 UTC. **Never submit to Kaggle.**

## Question

Claude's `rr0928` evidence says public `tetsu_base` narrowly beats `es7_wm` but all `es*`
agents crush other public agents.  Determine whether the edge is attributable to market
orders, by good/day/price and by shared-market contention in true mirrors.

## Predeclared method

- Use 16 fresh worlds each for `tetsu_base` vs `es7_wm` and `tetsu_base` vs itself, both
  seats, saved local replays only long enough to mine them.
- Cap this agent at 16 game workers (Claude's active `rr0928` already consumes significant
  CPU); use the official local runner and `/workspace/solution_kaggri/.venv/bin/python`.
- Parse per-player market execution (`BUY`/`SELL`, good, day, price, quantity) and daily
  money/state snapshots.  Attribute final money by executed sales revenue, purchase spend,
  animals/land, and residual terminal cash; compare paired worlds/seats.
- Delete raw transient replay files after parsing because free space is about 2.8 GiB.

## Deliverable

`research/t044_tetsu_edge.md`: measured edge decomposition and a ranked list of concrete,
tape-safe, append-only market-order rules with activation parameters.  No implementation,
candidate, or Kaggle action in this task.

## Result

Completed 2026-09-28 22:18 UTC.  16 fresh whole worlds × both seats for each requested
matchup (64/64 DONE); raw replays removed after hook parsing.  `tetsu_wm` rather than
base tetsu is +$24.88/world (paired bootstrap 95% +$6.81…+$47.75), entirely from a
$14.62 WHEAT cash delta plus +$10.25 EGG/FERTILIZER drift; animal buys, land, hires and
all other flows agree.  Exact tetsu mirror is 16/16 cash draws and shared sale prices are
identical.  Full evidence and bounded screen rules: `research/t044_tetsu_edge.md`.
