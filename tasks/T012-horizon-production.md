# T012 — Horizon production overrides (owner: codex, handed over from claude 2026-09-24 01:10)
Goal: make Horizon v5 produce more like M&M&P&Q (#1 LB) without breaking its tape machinery.
Evidence (T011): mmpq wins via earlier land (d5/d8 vs Horizon d6/d11), more strawberry (42 vs 33 seeds; 314 vs 249 sold), fertilizer used on strawberries instead of sold (144 vs 345 sold), more wheat, herd profile from bc_daily (codex's median: d8 6/3/0 → d12 8/3/5 cows/sheep/geese).
Hard gate: paired both seats vs **tape_mmpq_26860 + opponents/mmpq_bank hardest tapes (ep112572059, ep112604766, ep112586323, ep112554884)**, v5_market, v4_8turn, parthenos_robust, tschinkel_metav4_v13; dev seeds (not confirmation).
Note: Claude runs T013 in parallel (Horizon chassis driven by a whole mmpq tape) — different mechanism, same target. Compare results in the ledger.

## Execution log

- 2026-09-24 01:xx UTC — Codex added narrow `horizon_v5_mmpq_overlay.py` (commit `5e2afc3`): only d5--d11 existing SELL FERTILIZER + BUY_SEED STRAWBERRY orders are changed, retaining all but eight fertilizer units and adding at most nine strawberry seeds funded by the retained quote. Routes, herd, land and tape machinery are untouched. Smoke versus v5_market: 0 errors, exact 0 margin on one paired world. Two-world smoke versus `tape_mmpq_26860`: 4/4 (+32,437 mean; worst +1,771), while self-match stayed 0 margin. This is only a smoke and does not establish that the conditional rewrite fired; next step is action-attribution then the full hard gate.
