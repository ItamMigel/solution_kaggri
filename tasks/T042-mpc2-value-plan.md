# T042 — one-day value-MPC plan layer

Owner: codex. Status: complete. Never submit to Kaggle.

## Scope

Implement `lab/re/top_re/plan_mpc2.py`, keeping the `desired(obs, player)` and
`targets(obs, player)` interface. It must read the bundled JSON model
(`agents`, `wm`, `value`), condition its world model on `top_re` (falling back
to the nearest trained agent), sample a bounded set of tomorrow macros, score
only their predicted expected final margin, apply a normalised trust penalty,
then reuse the flow-plan tile layout. Bundle selection is `TOPRE_PLAN=plan_mpc2`.

Validation: run supplied tiny JSON only for plumbing, with at most six workers
and <0.3 seconds per simulated day. No model-quality conclusion from smoke.

## Result (2026-09-26)

Implemented `lab/re/top_re/plan_mpc2.py` and `TOPRE_PLAN=plan_mpc2` handling
in `bundle.py`.  The plan takes 12 tomorrow-only FM samples (8 integration
steps), scores each with value output 0 (`E[final margin]`) minus a
normalised one-day trust penalty, and lays out that selected macro through the
same crop/structure layout contract as `plan_fm`.  There are no future model
rollouts.  Agent conditioning selects exact `top_re`; if absent, it uses a
deterministic closest normalised agent name.

Smoke used only the supplied tiny immutable JSON via `TOPRE_MODEL=...`:
`TOPRE_PLAN=plan_mpc2 TOPRE_MODEL=<models.json> python bundle.py /tmp/topre_mpc2_smoke.py`.
An official-engine seed-778 run against frozen es7 finished `DONE/DONE`
($42,775 vs $174,831).  Its maximum agent call was 0.016857 s and maximum
aggregate calls in a day 0.047792 s.  The tiny model does not contain
`top_re`, so its documented fallback was `Boey`.  This validates plumbing and
runtime only, not model quality.
