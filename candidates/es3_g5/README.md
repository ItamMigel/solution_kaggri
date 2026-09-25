# Candidate es3_g5 — CMA-ES v2 (gen-5 centre) knobs + Horizon+ M1 COLLECT  ← CURRENT RECOMMENDATION
Archive `es3_g5.tar.gz` (main.py + LICENSE.txt + NOTICE.txt; sha256.txt). Agents never submit — the human decides.
= Horizon v5_market + 24 knobs from cma2 (warm-started at es1_g9, fitness includes the mirror vs es2_c1) + the idle-unit
COLLECT_FERTILIZER module of es2_c1. Knobs vs g9: _ADV_LOOK 15→17, _RACE_HORIZON_CLONE 8→10, _CA_CASH 922→1061, _Y_MARGIN −7→−2,
lower herd-gain thresholds (_HD2_MIN_GAIN 908→819, _CS_MIN_GAIN 597→463) … (params.json).
Archive smoke: 4/4 DONE, 719/719 calls.
## Evidence (0 errors, both seats, official engine)
| test | by | worlds | result |
|---|---|---|---|
| cma2 gen-5 centre gate | codex | 8 fresh | vs es2_c1 15-0-1, +$281 [157,395] |
| promotion gate | claude | 16 fresh | vs es2_c1 **32-0** (+$704, worst +9); vs es1_g9 32-0 (+$725); vs v5×2 28-4 (es2_c1 on the same seeds is also 28-4 → no regression) |
| independent review T026 | codex | 16 own | vs es2_c1 **30-0-2** CI [84.4,100]% (+$469); 9-opponent panel 271-0-17, paired score vs es2_c1 = 0 everywhere (no loss); fukami margin −$242 w/o score loss |
## Recommendation
Put es3_g5 on the ladder. It supersedes es2_c1 and es1_g9 (beats both 32-0). Current actives (2026-09-25): es1_g9 (56532237) and a
teammate experiment (56550803, 12:45). Submitting displaces the OLDER active = es1_g9 → pair = teammate experiment + es3_g5.
