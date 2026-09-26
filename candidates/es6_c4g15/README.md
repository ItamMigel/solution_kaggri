# Candidate es6_c4g15 — CMA4 gen-15 centre (+COLLECT)  ← CURRENT RECOMMENDATION (2026-09-26 10:30Z)
Archive `es6_c4g15.tar.gz` (sha256.txt). Agents never submit — the human decides. Archive smoke: 2/2 DONE, 719/719 calls.
= Horizon v5_market + 24 knobs from cma4 (warm start es5_c3g15; wide rotating panel fitness from gen 14) + COLLECT module.
Knob moves vs es5_c3g15 are small (_ADV_LOOK 19→20, _HD2_MIN_GAIN 805→1013, _Y_MARGIN −8→−10, …; params.json).
## Evidence (official engine, both seats, 0 errors, paired vs es5_c3g15 on the same fresh worlds)
| gate | by | worlds | panel paired (10 opps, equal weight) | notes |
|---|---|---|---|---|
| T025 fresh full-panel | codex | 16 | +5.56pp, one-sided lower +3.1pp, PASS | h2h vs es5 29/32; es1_g9 +2, parthenos +2, others equal |
| independent confirmation | claude | 16 other | +3.12pp, lower +1.56pp, PASS | h2h vs es5 **24/32** (+$360); parthenos 30 vs 28; the other 8 opponents identical scores, margins within ±$150 |
Honest reading: the gain is mostly the head-to-head vs es5_c3g15 (our own previous best) with **no regression anywhere** on 9 other opponents.
## Recommendation
Submit es6_c4g15 (human decision). Lineage: es1_g9 → es2_c1 → es3_g5 → es5_c3g15 → es6_c4g15.
