# T026 — Independent es3_g5 review (owner: codex, 2026-09-25)

Claude requested a headless red-team review of `/workspace/shared/candidates_wip/es3_g5/main.py` (CMA2 gen-5 centre plus M1 COLLECT), against frozen `/workspace/shared/candidates/es2_c1/main.py`.

## Locked method and decision rule

- Fresh, non-confirmation whole-world seeds, generated independently here and checked against saved run manifests: `1971817380, 726774209, 1419193724, 1247901682, 1505664428, 59285509, 1091288136, 1404948173, 1882273155, 1611276782, 382612970, 797842814, 824296276, 1256729625, 281988520, 1530188946`.
- Both seats; at most 20 workers; official local `compare.py`, no Kaggle access/submission.
- Evaluate both `es3_g5` and `es2_c1` against `v5_market`, `v5_guarded`, yhay routers 0913/0909, parthenos_robust, tschinkel_metav4_v13, tschinkel2945, ozer_v45, and fukami_v48. Evaluate `es3_g5` head-to-head against `es2_c1` separately.
- PASS only if es3_g5's h2h whole-world score CI lower bound exceeds 50%, and no panel opponent has an es3_g5-minus-es2_c1 paired-score CI wholly below zero. Any game error is invalid/fail.

## Result

**PASS.** H2H at `runs/t026_es3g5_review_codex_20260925/h2h/` is valid (32/32, zero errors): es3_g5 beats frozen es2_c1 **30–0–2**, score 93.75%, whole-world bootstrap CI **[84.4%, 100%]**, mean +$468.6.

The matching 16-world, nine-opponent paired panel at `runs/t026_es3g5_codex/panel/` is also valid (576/576, zero errors). es3_g5 is 271–0–17 overall. Its paired score gain (`es3_g5 − es2_c1`) and 95% whole-world CI, per opponent:

| opponent | paired score gain | 95% CI |
|---|---:|---:|
| v5_market | 0.000 | [0.000, 0.000] |
| v5_guarded | 0.000 | [0.000, 0.000] |
| yhay_router0913 | 0.000 | [0.000, 0.000] |
| yhay_router0909 | 0.000 | [0.000, 0.000] |
| parthenos_robust | 0.000 | [−0.188, +0.188] |
| tschinkel_metav4_v13 | 0.000 | [0.000, 0.000] |
| tschinkel2945 | 0.000 | [0.000, 0.000] |
| ozer_v45 | 0.000 | [0.000, 0.000] |
| fukami_v48 | 0.000 | [0.000, 0.000] |

Thus no opponent has es3_g5 significantly worse in paired **score**, which is the predeclared panel gate. Some margin deltas are negative (notably fukami −$242, CI [−$477, −$59]), but no score loss accompanies them and margin was not the stated rejection criterion. Candidate source hash remained `fb194f51d3227472afbb9f4169b30e1706f46636cbe0232f0fa17e988cb231b1`.
