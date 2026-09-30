# T047 result review — Claude (independent recomputation, 2026-09-30 09:06Z)

Input: `/workspace/shared/runs/t047_m26_post/games.jsonl` after all 192 rows were written (09:04Z). I launched no games.
Recomputed from raw rows with my own script (independent RNG, 100k whole-world bootstrap).

**Update 09:10Z:** stale-summary warning resolved — `summary.json` now 192 records, `complete: true`, errors 0. The
`summarize` empty-worlds path only short-circuits at n==32/worlds==16, so no empty-data bug. `loader_smoke.json`: 6/6 rows
(terminal/a1/dsm75_mg25 × seat 0/1), all DONE/DONE, `parity: true`. Unchanged-parent control
(`sanity_control.jsonl`, 32 m26-vs-tetsu/ozer44 games) complete, 0 errors.

## Integrity
192/192 unique keys = manifest jobs; 0 invalid; all DONE/DONE, 719/719 calls; zero BC/HG/terminal fallback errors in both
players of every game; `remainingOverageTime` 60 everywhere; max single-call latency 0.41 s (< actTimeout 1 s).

## Numbers (candidate perspective)
| variant | opp | W/D/L | points | mean margin | world 95% CI (mine) |
|---|---|---|---|---|---|
| terminal | m26 | 24/0/8 | 24/32 (.75) | +$190.22 | [+96.2, +298.6] |
| terminal | tetsu | 16/0/0 | 16/16 | +$23,138 | — |
| terminal | ozer44 | 14/0/2 | 14/16 | +$19,987 | — |
| a1 | m26 | 8/16/8 | 16/32 | $0.00 | [0, 0] |
| a1 | tetsu | 16/0/0 | 16/16 | +$23,269 | — |
| a1 | ozer44 | 14/0/2 | 14/16 | +$19,954 | — |
| dsm75_mg25 | m26 | 15/0/17 | 15/32 | −$1,922.56 | [−3,951, +74] |
| dsm75_mg25 | tetsu | 16/0/0 | 16/16 | +$13,297 | — |
| dsm75_mg25 | ozer44 | 16/0/0 | 16/16 | +$16,945 | — |

Matches Codex's terminal figures (+190.21875, CI [96.81, 299.44]; bootstrap RNG differs only).
Gate as frozen: **terminal PASS; a1 FAIL; dsm75_mg25 FAIL.**

## Interpretation
- **terminal.** Against m26, the a1 games are a pure m26 mirror (16/16 worlds exactly antisymmetric), so a paired own-cash
  delta can be computed per game: **32/32 ≥ 0 (min $0, mean +$190.2); opponent reward changes by exactly $0 in all 32**. So the
  effect is a pure end-of-game own-cash gain, not harm to the opponent. The 24/32 points come from turning mirror draws into
  +$23…+$134 wins; that is not evidence of a rating gain against the field. The real effect is ≈ +$190/game (~0.2% of a
  typical $70–115k score): it can only decide very close games. Low-risk in this panel; **not** a universal monotonicity proof — nonnegative own-cash deltas were only observed here,
  and a terminal action can interact with the market/opponent (cf. the withdrawn T045 monotonicity claim).
- **Sanity confound — resolved by the unchanged-parent control.** Paired vs m26 control (same opp/world/seat), terminal:
  own Δ 32/32 ≥ 0 (mean +$264); margin Δ tetsu +176.375, ozer44 +352.0 (min 0/+1), points 16/16 and 14/16 identical to
  parent (Δ 0). Opponent reward changes only in tetsu w93047102 (−$1, both seats) — terminal-step spillover. a1 vs control
  diverges exactly in the two worlds I flagged (tetsu w93047103 own +$2,242; ozer44 w93047105 own +$6,927), so the earlier
  divergence was a1 behaviour, not terminal and not opponent nondeterminism. dsm75_mg25 diverges in 32/32 (margin Δ mean
  −$6,177), confirming it as a real policy change and a regression.
- **a1.** Exactly antisymmetric h2h margins (m26 mirror) are consistent with non-activation in that panel, but without
  action telemetry they do not prove it; the h2h gate cannot measure its effect. The sanity control shows it can
  change play vs tetsu/ozer44 (see above). No promotion from this evidence.
- **dsm75_mg25.** Clear regression: −$1,923/game vs m26 (CI upper barely +$74) and much lower sanity margins than a1/terminal
  (tetsu +$13.3k vs +$23.3k; ozer44 +$16.9k vs +$20.0k). Reject.

## Recommendation
terminal may be frozen via `package.py` **— both preconditions (refreshed `summary.json`, 6/6 loader-smoke parity) are now met. The README must
describe the gain as ≈ +$190/game own cash, never negative in the observed paired games (not a guarantee); the 75% h2h points should not be presented as a
strength signal. The human decides on submission; no agent submits.
