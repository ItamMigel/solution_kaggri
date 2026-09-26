# Candidate es5_c3g15 — CMA-ES v3 (gen-15 centre) knobs + Horizon+ M1 COLLECT  (superseded 2026-09-26 by es6_c4g15)
Archive `es5_c3g15.tar.gz` (main.py + LICENSE.txt + NOTICE.txt; sha256.txt). Agents never submit — the human decides.
= Horizon v5_market + 24 knobs from cma3 (warm-started at es3_g5, mirror opponent es3_g5) + COLLECT_FERTILIZER module.
Main knob changes vs es3_g5: _ADV_LOOK 17→19, _V92_P_H 61→67, _RACE_HORIZON_CLONE 10→7, _Y_MARGIN −2→−8, _CS_MIN_GAIN 463→842,
_CS_RATIO 1.31→0.95, _FD_WIDTH 8→10 (params.json). Archive smoke: 2/2 DONE, 719/719 calls.
## Evidence (official engine, both seats, 0 errors)
| test | by | worlds | result vs es3_g5-on-same-worlds |
|---|---|---|---|
| gen-15 centre gate, h2h | codex | 8 fresh | vs es3_g5 **16-0** (+$836) |
| parthenos+metav4 paired | codex | 24 + 24 fresh (48) | 90-6 → combined +5.2pp vs es3_g5, one-sided 95% lower 0.0pp (NI −2pp PASS) |
| 9-opponent panel | claude | 8 fresh | parity on 7; es1_g9 10-6 vs 12-4, v5 14-2 vs 16-0 (margins equal/better) |
| Horizon-family paired | claude | 24 fresh | vs es1_g9 **48-0** (+766) vs es3 46-2 (+577); vs v5 44-4 (+784) vs 44-4 (+693); paired +2.1pp, +$140; NI lower −4.2pp (24 worlds, few discordant games — bound not informative) |
Caveat: the family NI bound is below −2pp only because of sample size; all point estimates favour es5_c3g15.
## Recommendation
Replace es3_g5 with es5_c3g15 on the ladder when the human decides (keep es3_g5 as the other active if the teammate slot is free).
Previous: es3_g5 (candidates/es3_g5). es4_c3g5 rejected (parthenos regression).
