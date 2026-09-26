# T036 — production reverse engineering

Owner: codex. Scope: infer explicit, teacher-forced production rules from `research/re/*.jsonl.gz` for Boey, M&M&P&Q, DSM, and fuxi: crop/planting/fertilizer policy; per-turn unit allocation and priority; herd/structure timeline. Excludes market and macro decision logic (Claude).

Method: use state/action decision logs, derive state-gated rules on a development episode subset, and report held-out action agreement by rule and action class. Record episode identifiers and coverage; avoid claiming a rule where action fields do not expose the needed state.

Result (2026-09-26): completed Boey (108), M&M&P&Q (134), DSM (103), and fuxi (40) trajectory production profiles with held-out teacher-forced aggregate-action agreement; `research/re_production.md`. Raw action audit gives quadrant-level layout rules. The requested M&M&P&Q/DSM d0–d9 fixed-opening test is negative: pooled held-out exact production-vector agreement is 30.6% (4,401/14,400), so it is not a shareable tape. No evidence-supported d8+ Horizon herd graft exists: the sole tape-safe G1 only owns d0–3 and its 2-goose leg already failed T028 (0/8, −$2,581). Therefore no duplicate implementation/screen was run. Feed the explicit crop/herd/service rules into a standalone top-RE opponent with its own state/path planner, not a claimed Horizon reconstruction. No candidate or Kaggle action.
