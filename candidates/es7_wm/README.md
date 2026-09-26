# Candidate es7_wm — es6_c4g15 + market-only WHEAT trading layer (T031)  ← CURRENT RECOMMENDATION (2026-09-26 15:10Z)
Archive `es7_wm.tar.gz` (sha256.txt). Agents never submit — the human decides. Archive smoke: 2/2 DONE, 719/719 calls, max 487 ms/step.
= es6_c4g15 (Horizon v5_market + cma4 gen-15 knobs + COLLECT) + Codex's default-ON wheat market layer (lab/hplus/wheat_market.py):
buys WHEAT products when cheap and sells after town consumption restores the price — market orders only, no unit actions (tape-safe).
Origin: opponents in our 39 ladder losses buy +529 wheat (d12.8 @$6.94) and sell later (d20.3 @$8.58).
## Evidence (official engine, both seats, paired vs es6_c4g15 on the same fresh worlds, 0 errors)
| gate | by | worlds | panel paired | notes |
|---|---|---|---|---|
| T025 full panel | codex | 16 | +4.17pp, lower +3.13 PASS | h2h vs es6 27/32; es1_g9 +2; all others ≥ 0 |
| independent confirmation | claude | 16 other | **+6.88pp, lower +5.00 PASS** | h2h vs es6 **30/32**; +2 vs es5_c3g15, v5_market, demand-preserving, shepherd; margins +~$50 vs every Horizon-family opponent; none worse |
Honest reading: tiny $ edge that flips near-mirror games; the public/ladder field is Horizon-heavy, so it matters.
## Recommendation
Submit es7_wm (human decision). Lineage: es3_g5 → es5_c3g15 → es6_c4g15 → es7_wm.
