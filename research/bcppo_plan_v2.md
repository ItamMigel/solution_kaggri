# BC → PPO v2 — joint plan (Claude + Codex), 2026-09-24 evening
Sources: research/bcppo_design.md (Claude draft), research/bcppo_design_codex.md (Codex review). Claude verified Codex's two
key claims in the engine source: (1) units MAY walk onto LOCKED tiles (kaggriculture.py `_apply_unit_action`: "Movement onto
LOCKED tiles is allowed"); (2) market fills per unit, so buys partially fill and earlier SELLs fund later buys.

## Goals (agreed)
- Track B (3 GPUs): strong reactive **doubles** of top teams (DSM, M&M&P&Q, Mother-Goose) — evaluation opponents we lack today.
- Track A (1 GPU): strongest agent. Honest prior: beating es1_g9 in 5 days is unlikely; g9 stays the submission unless an
  external paired gate says otherwise.

## Must-fix before any long run (blockers)
| # | fix | owner | file |
|---|---|---|---|
| F1 | allow moves onto LOCKED (mask only out-of-board) — GPU policy AND numpy export | claude | policy.py, export.py |
| F2 | market: no client-side affordability filter (engine does exact partial fills / sale-funded buys); fixed order; cap 10 orders; log-prob only over keys actually emitted (incl. zero decisions), not over truncated ones | claude | policy.py, export.py |
| F3 | sequential allocator farmer→hands: PLANT per crop ≤ seeds (engine cancels ALL plants of a crop if over-demanded), PICKUP ≤ remaining shed, PLACE animal only on matching empty structure (COOP↔goose, PASTURE↔cow/sheep), PLACE product only shed-adjacent | claude | policy.py, export.py |
| F4 | stochastic direction when off-target: sample among legal distance-reducing moves with log-prob & entropy (not argmax) | claude | policy.py, export.py |
| F5 | hand cap: mask HIRE when n_hands+hires ≥ 16 (gpuenv MAX_HANDS); same in export | claude | policy.py, export.py |
| F6 | checkpoint carries architecture (ch, blocks, teams, vocab); PolicyNet built from it; N-team BC; per-team or conditional | claude | train.py, policy.py, export.py |
| F7 | streaming rollout buffer (preallocated tensors, fp16 board, no list+stack+concat), start 256–512 env/GPU, measure peak | codex | ppo.py |
| F8 | reward: zero-sum Δ(equity_own − equity_opp), equity = cash + conservative liquidation value (shed/seeds/animals/mature crops via market curve); terminal correction to cash margin; gamma 1.0 (≥.9999), lambda .995 | codex | ppo.py (+ equity fn on State) |
| F9 | metrics: approx-KL, clipfrac, explained variance, per-head entropy, executed-op distribution, rejected/no-op counts; critic warm-up (value-only iters) before policy updates; optimizer/RNG in resume | codex | ppo.py |
| F10 | league: per iteration split envs into chunks with different opponent nets: 35% frozen own snapshots, 30% current, 25% other doubles, (10% tape stressor later/optional) | codex | ppo.py |
| F11 | tests: decoder→gpuenv→official round-trip incl. LOCKED crossing & shed-access, partial fills & sale-funded buys, hand cap, 719-step export timing; e2e must stay 0 diffs AFTER F1–F5 | claude (+codex review) | parity/e2e tests |

## Data (claude, parallel with fixes)
Pull all available episodes of active subs for top ~10 LB teams (≥ DSM, M&M&P&Q, Mother-Goose, DECEM, Vadim …), build BC data per team.
Keep losses with outcome weight (no survivorship). BC eval metrics: effective-action accuracy after masks+decoder,
non-zero market precision/recall, qty MAE (not zero-dominated key acc).

## H100 schedule (after F1–F11 pass here)
- 0–4 h: GPU0/1/2 BC v3 per team (DSM / M&M&P&Q / Mother-Goose); GPU3 conditional multi-team. Compare held-out effective behaviour.
- 4–24 h: GPU0 = track A (best BC + mixed league); GPU1–3 = one double each (BC-KL floor for style).
- Stop rule: track A with no lower-CI gain vs its own BC base and no wins in the external mini-gate → GPU goes to best double.
- Returns to us: validity/value/double-vs-holdout first; then official both-seat gate vs g9/v5/panel.

## Division of labour
Claude: F1–F6, F11, data pull/build, packaging. Codex: F7–F10 in ppo.py (+ equity fn), review of F1–F6 diffs, gate design.
Interface frozen: `policy.act(net, st, p, so, team, greedy) -> (actions_p, logp[B], value[B], ent_parts: dict, rec: dict)`,
`policy.logprob(ul, tl, ml, rec) -> (logp, ent_parts)`. Codex works in lab-codex on ppo.py only; Claude on the rest.
