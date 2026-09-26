# T037 — standalone top-RE units layer

Owner: codex. Status: in progress. Never submit to Kaggle.

## M4 walking reduction (claimed 2026-09-26)

While Claude evaluates logit-greedy versus Hungarian on the 8-seed integrated
agent, Codex owns only the units-layer follow-up: morning-rebalanced,
per-unit farm zones and an observation-safe short route commitment.  The
dispatcher must not make cross-farm trips except for same-turn FEED/WATER
deadlines.  Compare the bundled agent on seeds 777/778/779 with at most six
workers using `telemetry_run.py`; report PASS/move share, FEED/WATER counts and
cash.  This is a local integration measurement, never a candidate or Kaggle
action.

Scope: independently critique the M1/M2 schedule and implement `lab/re/top_re/units.py` only: state-aware task generation, greedy assignment, and legal movement returning `(farmer, hands)` from `units.act(obs, plan)`. Claude owns `plan.py`, `market.py`, and integration.

Acceptance: imports with only stdlib; handles the Kaggle observation/action schema; never emits an illegal walk/operation when sufficient state is supplied; assigns every controlled unit exactly one action; has a small local legality test/smoke. Findings go to `research/top_re_agent_plan_codex.md` and BOARD.

## Result (2026-09-26)

Implemented `lab/re/top_re/units.py` (stdlib only). It supports explicit `plan.tasks(obs)` task dicts and target maps (`plant_targets`, `build_targets`, `place_targets`, `fertilize_targets`); it reserves duplicate tile operations, uses observed inventories/seeds/shed capacity, and returns `(farmer, hands)` only. Synthetic operation tests cover pickup/feed, plant/place and full-shed non-drop; two `units.action` agents also completed a full 720-step official kaggle-environments smoke episode as `DONE/DONE` (both $2,750, deliberately primitive wheat-only market).

Interface sent to Claude. Still required before a score claim: merge with plan/market, log requested vs executed work, and run full legal games.

## M3 min-cost assignment and feed-cargo validation (2026-09-26, Codex)

- Replaced the greedy dispatcher with a stdlib Hungarian minimum-cost bipartite assignment. Its cost is Manhattan movement cost minus conditional-logit task utility from the committed MMPQ `task_weights.json`; the one-file bundle has the identical checked-in coefficient fallback. Every assigned endpoint is still checked with the current observed inventory/state before it emits an operation; padded dummy jobs leave a worker idle only when no legal work is available.
- Logistics now splits WHEAT pickup into load-sized batches based on the number of unfed animals. A debugging run exposed an initial defect: WHEAT was incorrectly eligible for `DROP`, producing 662 pickups/580 drops and starving animals. WHEAT, fertilizer and unplaced animals now remain route cargo; only saleable products create DROP tasks. A survival floor prioritises daily FEED and its prerequisite WHEAT pickup, with an extra penalty after a missed feed.
- Official-engine bundled smoke against frozen `es7_wm`, same full plan/market and seeds **777/778/779**, completed normally. New dispatcher rewards: **$69,860 / $53,181 / $39,399**; the `units_simple` control on exactly the same worlds is **$56,266 / $44,266 / $38,919**. That is +$13,594 / +$8,915 / +$480 (mean **+$7,663**); FEED counts are 311/305/314 and final weeds 0/3/2. This is an integration smoke only, not a candidate or Kaggle claim.
- Source commits `7afd23b`, `bd934ae`, `1b98508` are merged into primary `lab` at `1b98508`. Claude retains ownership of plan/market and any wider evaluation.

## M4 result — walking reduction screen (2026-09-26, Codex)

- Updated `lab/re/top_re/telemetry_run.py` to print both PASS and cardinal-move shares.  Rebuilt the unchanged Hungarian bundle and ran it as player 0 against frozen `es7_wm` on 777/778/779: cash **$69,860 / $53,181 / $39,399** (mean **$54,147**); PASS **9.3 / 9.7 / 9.4%**; moves **44.0 / 45.1 / 43.4%**; FEED **311 / 305 / 314** and WATER **1,232 / 1,189 / 1,242**.  This establishes the reported ~50% walking problem precisely.
- A morning-rebalanced contiguous per-unit-zone prototype with cross-zone work allowed only for `consecutive_unfed>=1` or `consecutive_unwatered>=1` is decisively unsafe on exactly those worlds: **$14,851 / $13,414 / $16,677** (mean **−$39,166** vs baseline), PASS **32/37/35%**, FEED **116/106/97**, WATER **860/804/836**.  It creates idle islands while daily work is spatially unbalanced.
- Even the relaxed two-nearby-stop route commitment (no cross-zone penalty) remains bad: **$49,662 / $29,863 / $35,063**, mean **−$15,951**, PASS **20/18/19%**, FEED **273/243/267**, WATER **914/914/915**.  Stateful routes miss newly available service work; the prototype was reverted, so `units.py` remains the merged stateless Hungarian dispatcher.  Keep the telemetry improvement only.

Disposition: reject persistent strict zones and fixed multi-stop commitments.  Any next walking idea must preserve global reassignment each turn and prove no loss of FEED/WATER before a wider score gate; a future safe direction is only a one-turn tie-break/locality penalty, not persistent ownership.
