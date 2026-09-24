# Candidate es1_g1 — Horizon v5_market + ES-tuned knobs
**Archive:** `es1_g1.tar.gz` (main.py + LICENSE.txt + NOTICE.txt; sha256 in sha256.txt). Agents never submit — the human decides.
**What it is:** exactly `agents/horizon_v5_market.py` plus one appended `globals().update({...})` with 24 tuned knob values (`params.json`), found by an evolution strategy on the real engine (T018, `lab/tools/knob_es.py`, gen-1 centre). No new logic, no external files.
## Evidence (all 0 errors, both seats, official runner)
| test | worlds | result |
|---|---|---|
| Claude validation (fresh, non-confirmation) `runs/val_es1_g1` | 16 | vs v5_market **30-2** (+515), vs v5_guarded **30-2** (+515), vs v4_8turn **32-0** (+1311) |
| Codex independent reproduction (own excluded worlds) `runs/t018_independent_codex_*` | 16 | **244-0-12** overall; vs v5_market 31-1 (+425); yhay0913/0909 31-1; metav4, t2945, ozer, fukami 32-0; parthenos 23-9 |
| Paired vs parthenos on codex's worlds `runs/parthenos_pair` | 16 | es1_g1 23-9 (+871) vs v5_market 25-7 (+995) — slight, non-significant regression |
| Archive smoke (extracted tarball, official loader) | 2 | 4/4 vs v5_market, 719/719 calls, DONE |
## Caveats
- Edge over v5 is small per game (~+$400–500) — valuable mostly in mirror/clone games, which are most of the ladder.
- Not tested against the real top-50 reactive agents (can't simulate them). parthenos is the one opponent where it is not better.
- Local max decision time ≈0.9 s on a loaded box, same as v5 (v5's overage on Kaggle stayed ≥59.8 s of 60).
## Recommendation (claude + codex, T016)
Active pair at deadline: **v5_guarded + es1_g1** (drop v5_market, which is near-identical to guarded: 118/128 draws head-to-head).
Note on ladder slots: only the 2 most recent submissions stay active. v5_market (56504560, 22:03:01) is older than v5_guarded (56504572, 22:04:08), so submitting es1_g1 displaces v5_market and leaves exactly **v5_guarded + es1_g1** active — no re-submission of guarded needed.
