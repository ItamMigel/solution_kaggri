# Candidate es1_g9 — Horizon v5_market + ES-tuned knobs (gen-9 centre)  ← CURRENT RECOMMENDATION
Archive `es1_g9.tar.gz` (main.py + LICENSE.txt + NOTICE.txt; sha256.txt). Agents never submit — the human decides.
Exactly `agents/horizon_v5_market.py` + one appended `globals().update(params.json)`. Archive smoke: 4/4 DONE, 719 calls.
## Evidence (0 errors, both seats, official runner)
| test | by | worlds | result |
|---|---|---|---|
| h2h vs es1_g1 | claude | 16 fresh | **32-0**, +712 (worst +9) |
| h2h vs v5_market | claude | 16 fresh | **32-0**, +705 |
| h2h vs es1_g1 | codex (independent worlds) | 16 | **31-1**, +635, 95% CI +366…+948 |
| vs v5_market + v5_guarded | codex | 16 fresh | **64-0**, +562 (es1_g1 on same worlds: 60-4, +466) |
| reactive panel (yhay0913/0909, parthenos, metav4, t2945, ozer, fukami, v4_8turn) | both | 16+16 | tied with es1_g1 (no regression) |
## Recommendation (claude + codex)
Active pair at the deadline: **v5_guarded + es1_g9**. Submitting es1_g9 displaces the older of the two active subs.
Check current actives first (teammates uploaded horizon_v6_repair on 2026-09-24 13:08 UTC): `kaggle competitions team-submissions 16739419`.
