# T047 code review — Claude (independent, 2026-09-30 ~09:05Z)

Scope: `/workspace/wt/codex/lab/t047/{build,gate,summarize,check,loader_smoke,package}.py`, `manifest.json`, `fixtures.json`,
base `/workspace/shared/research/t046_ft/agents/m26dsm/main.py`. Nothing launched by me except read-only
analysis of `runs/t047_m26_post/games.jsonl`. Never submit.

**Verdict: code PASS — no blocking defects.** Three exports are exactly the single changes they claim; the gate's error
accounting is sound; a few non-blocking notes below.

## Provenance / single-change check
- sha256 of all 4 exports match `manifest.json`; `build.py`, `gate.py`, `terminal.py` match `provenance.json`
  (terminal.py `912d26…` = the T045 reviewed file).
- `diff` base→export (verified by me):
  - `a1`: exactly 3 lines (`protected = set()`, `protected.add(i)`, `free = … - protected`). Nothing else.
  - `dsm75_mg25`: only the `_T047Weighted` class + `_AG.model = …` inserted after the `_AG = Agent(...)` line.
  - `terminal`: only an append after the HG `agent` (engine source + terminal.py exec'd into private dicts, outermost wrapper).
  - `m26` byte-identical to base (asserted in build.py).

## terminal
- `liquidate(..., enabled=True)` returns the action object unchanged unless `step == 718` (last of 719 calls; `episodeSteps` 720).
  HG is a no-op at `step >= 718`, so the terminal wrapper is the only change at that tick. Same call signature/flag as T045 fixtures.
- Exception → parent action + `_T047_ERRORS['terminal']` counted by gate. BC exceptions still produce the PASS fallback and liquidate runs on it (fine).
- Cosmetic: the new outer `agent` loses `agent.telemetry` (unused by Kaggle). Import cost: one extra exec of the engine subset — negligible.

## A1
- Semantics correct: a unit already doing native FEED on an urgent animal is no longer re-assignable by HG to a second urgent
  animal (m26 bug: it would be overridden to walk away, so neither animal gets fed this turn). `check.py` fixture proves
  m26→`EAST`, a1→`FEED` on the real exported source.
- **Note:** in the gate A1 was *never* active in 16/16 h2h worlds (see below: exact antisymmetric margins = pure m26 mirror).
  The gate does not record `_HG_STATS['overrides']`, so activation counts can't be read from `games.jsonl`. Suggest logging
  `_HG_STATS` per game in future gates.

## dsm75_mg25 mixture
- Two shallow copies share `W` (verified in check.py `is`), only `tv` changed to the `mgoose_cn` one-hot; weights
  `.375,.375,.125,.125` sum to 1. All heads mixed (`units` op+target, `qty`, `m_step`, `m_qty`); `encode`/`m_start` inherited
  from `_Ens` and iterate all 4 members. Unnormalized weighted log-prob = weighted geometric mean; policy is greedy so
  normalization is irrelevant. Correct as specified.
- Cost: 4 trunk passes instead of 2 → p99 ≈0.085 s vs 0.045 s, max 0.18 s; far under `actTimeout` 1 s, zero overage used.

## gate.py — fallback/error accounting, timing, seeds
- BC fallback: `mod._AG` replaced by a counting wrapper. This works because the first `agent` (renamed `_HG_PARENT`) looks
  up `_AG` in module globals at call time; the `_T047Weighted` model was attached before replacement. HG (`_HG_STATS['errors']`)
  and terminal (`_T047_ERRORS`) are module-level and read per module. `grep` finds only these `try/except` sites in the base
  (lines 375/497) + terminal wrapper → no other hidden fallback paths.
- Candidate and opponent are separate module objects (`t047_candidate` / `t047_opp`); only `sys.modules['feat'/'feat3']`
  is shared, and those hold no per-game state (UnitMemory is per-Agent). OK.
- `measured` has `co_argcount`=4, kaggle slices `[obs, config][:4]` → config passed. OK.
- Latency asserted as overage < 55 s with actTimeout 1 s; observed `remainingOverageTime` = 60 in every game.
- Assertions per game: DONE/DONE, 719 calls each, zero errors in **both** players, overage. Invalid rows are written but
  block a resume and fail `pass` (n==valid). Good.

## summarize.py
- Whole-world bootstrap (mean of both seats per world, 100k resamples, fixed RNG). Correct.
- **Methodological note (not a bug):** in an m26 near-mirror, 20/32 baseline games are exact draws (seat-asymmetric but
  deterministic). The `points >= .65` criterion is therefore mostly a tie-breaker counter: terminal gets 24/32 by turning
  exact draws into +$23…+$134 wins. The margin CI is the meaningful statistic. Since the pure-mirror world mean is exactly 0,
  terminal's world-mean margin **is** the liquidation delta.
- Sanity opponents (tetsu/ozer44) are only checked for completeness/zero errors, no performance floor — acceptable as designed,
  but should be stated so in any README.
- Minor: `h['world95'][0]` would crash if no complete world (only on empty data).

## loader_smoke.py
- Official path-string loading (`get_last_callable` on the real file) vs callable gate result on world 93047001 both seats,
  compares full rewards. For terminal, world 1 has a +$23 own delta in both seats, so parity is discriminating. Good.
  Must run after the gate completes (it asserts the matching row exists).

## package.py
- Requires `summary.complete`, `errors==0`, 6/6 loader parity, variant `pass`, a review file, sha match; refuses to overwrite;
  deterministic tar with only `main.py`. README text states no submission. OK. No Kaggle call anywhere in T047 code.
