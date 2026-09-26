# T037 — standalone top-RE units layer

Owner: codex. Status: in progress. Never submit to Kaggle.

Scope: independently critique the M1/M2 schedule and implement `lab/re/top_re/units.py` only: state-aware task generation, greedy assignment, and legal movement returning `(farmer, hands)` from `units.act(obs, plan)`. Claude owns `plan.py`, `market.py`, and integration.

Acceptance: imports with only stdlib; handles the Kaggle observation/action schema; never emits an illegal walk/operation when sufficient state is supplied; assigns every controlled unit exactly one action; has a small local legality test/smoke. Findings go to `research/top_re_agent_plan_codex.md` and BOARD.
