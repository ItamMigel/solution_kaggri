# T037 — standalone top-RE units layer

Owner: codex. Status: in progress. Never submit to Kaggle.

Scope: independently critique the M1/M2 schedule and implement `lab/re/top_re/units.py` only: state-aware task generation, greedy assignment, and legal movement returning `(farmer, hands)` from `units.act(obs, plan)`. Claude owns `plan.py`, `market.py`, and integration.

Acceptance: imports with only stdlib; handles the Kaggle observation/action schema; never emits an illegal walk/operation when sufficient state is supplied; assigns every controlled unit exactly one action; has a small local legality test/smoke. Findings go to `research/top_re_agent_plan_codex.md` and BOARD.

## Result (2026-09-26)

Implemented `lab/re/top_re/units.py` (stdlib only). It supports explicit `plan.tasks(obs)` task dicts and target maps (`plant_targets`, `build_targets`, `place_targets`, `fertilize_targets`); it reserves duplicate tile operations, uses observed inventories/seeds/shed capacity, and returns `(farmer, hands)` only. Synthetic operation tests cover pickup/feed, plant/place and full-shed non-drop; two `units.action` agents also completed a full 720-step official kaggle-environments smoke episode as `DONE/DONE` (both $2,750, deliberately primitive wheat-only market).

Interface sent to Claude. Still required before a score claim: merge with plan/market, log requested vs executed work, and run full legal games.
