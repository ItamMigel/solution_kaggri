# T036 — production reverse engineering

Owner: codex. Scope: infer explicit, teacher-forced production rules from `research/re/*.jsonl.gz` for Boey, M&M&P&Q, DSM, and fuxi: crop/planting/fertilizer policy; per-turn unit allocation and priority; herd/structure timeline. Excludes market and macro decision logic (Claude).

Method: use state/action decision logs, derive state-gated rules on a development episode subset, and report held-out action agreement by rule and action class. Record episode identifiers and coverage; avoid claiming a rule where action fields do not expose the needed state.

Status: in progress — 2026-09-26 redirect: exact DSM/M&M&P&Q d0–d10 layout, goose/coop placement and feeding routes; test whether their d0–d8 actions are a shared fixed opening across 100 episodes; then implement only a feasible Horizon d8+ variant and screen it vs es7_wm plus boatlee/fukami. No candidate or Kaggle submission action.
