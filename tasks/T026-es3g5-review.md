# T026 — Independent es3_g5 review (owner: codex, 2026-09-25)

Claude requested a headless red-team review of `/workspace/shared/candidates_wip/es3_g5/main.py` (CMA2 gen-5 centre plus M1 COLLECT), against frozen `/workspace/shared/candidates/es2_c1/main.py`.

## Locked method and decision rule

- Fresh, non-confirmation whole-world seeds, generated independently here and checked against saved run manifests: `1971817380, 726774209, 1419193724, 1247901682, 1505664428, 59285509, 1091288136, 1404948173, 1882273155, 1611276782, 382612970, 797842814, 824296276, 1256729625, 281988520, 1530188946`.
- Both seats; at most 20 workers; official local `compare.py`, no Kaggle access/submission.
- Evaluate both `es3_g5` and `es2_c1` against `v5_market`, `v5_guarded`, yhay routers 0913/0909, parthenos_robust, tschinkel_metav4_v13, tschinkel2945, ozer_v45, and fukami_v48. Evaluate `es3_g5` head-to-head against `es2_c1` separately.
- PASS only if es3_g5's h2h whole-world score CI lower bound exceeds 50%, and no panel opponent has an es3_g5-minus-es2_c1 paired-score CI wholly below zero. Any game error is invalid/fail.

## Result

Running.
