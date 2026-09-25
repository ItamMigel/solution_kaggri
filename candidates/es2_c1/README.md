# Candidate es2_c1 — es1_g9 + Horizon+ M1 "idle units collect fertilizer"  ← CURRENT RECOMMENDATION
Archive `es2_c1.tar.gz` (main.py + LICENSE.txt + NOTICE.txt; sha256.txt). Agents never submit — the human decides.
= exactly es1_g9 (Horizon v5_market + ES/CMA knobs) + one appended module: when the Horizon tape gives a unit a literal PASS and the
animal on its own tile has fertilizer available, it does COLLECT_FERTILIZER (no movement ⇒ the tape stays aligned). Everything else off.
Archive smoke: 4/4 DONE, 719/719 calls (official runner, extracted tarball).
## Evidence (0 errors, both seats, official engine)
| test | by | worlds | result |
|---|---|---|---|
| per-op ablation (M1) | claude | 8 | COLLECT vs g9 13-3; other ops neutral or negative (plant harvest 0-16) |
| race (locked fold) | claude/codex harness | 4 | paired vs genome0 +0.167, +$22 [+1,+43] |
| final stage (5 opponents) | claude | 8 | paired +0.0875 [+0.06,+0.10]; vs g9 15-1 (g9 self 1-14-1); others unchanged |
| promotion gate | claude | 16 fresh | vs es1_g9 **31-1** CI [90.6,100]% (+$15); vs es1_g1 30-2; vs v5_market/guarded 64-0 |
| independent review (T022) | codex | 16 own | vs es1_g9 **29-2-1** CI [84.4,100]%; reactive panel no regression; vs t2945 32-0 |
## Caveat
The edge is small in money (~+$10–20/game vs g9) but converts mirror/clone games into wins almost always — which is what most ladder games are.
## Recommendation
Active pair: **es1_g9 + es2_c1**. Submitting es2_c1 now displaces the older active (es1_g1, 56522075).
