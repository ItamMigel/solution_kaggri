# T032 — opponent-harvest forecaster

Owner: codex. Status: in progress. Priority task set 2026-09-26; deadline gate 2026-09-28 18:00 UTC. **Never submit to Kaggle.**

## Hypothesis

The shared observation exposes the opponent's crops/animals and their states. Forecasting imminent high-impact shared-market supply (MILK, WOOL, STRAWBERRY, MELON), conditioned on their observed sale behaviour, can safely advance an already-planned Horizon sale ahead of an opponent dump. It should be market-only and default-off, with exact output identity when disabled.

## Method

1. Start from `/workspace/shared/candidates/es7_wm/pkg/main.py`, copied only into Codex's worktree.
2. Build visible-farm maturity/yield forecasts plus conservative sale-behaviour evidence; use only an existing own planned SELL and no production/path changes.
3. Prove off-mode action identity against es7_wm. Measure steep-item temporal adjacency in the 39 ladder losses.
4. Capability screen on fresh paired, both-seat 2 worlds against parthenos, metav4, shepherd, and es7_wm mirror. Only a positive result proceeds to the declared T025 full panel versus es7_wm.

## Result

`experiments/t032_opponent_harvest/main.py` implements the bounded gene;
`main_on.py` changes only the feature flag. The enabled version records a
recent rival cash increase (a successful sale), counts public mature rival
MILK/WOOL/STRAWBERRY/MELON yield plus only conservative first-yield-date cases,
and advances an already planned own same-item SELL by at most 12 steps. It
never edits a unit action, buys, or route choice.

Default-off identity passes on two fresh worlds, both seats against Parthenos:
**0/2,876 action differences**, equal cash, 8/8 valid/DONE.
`runs/t032_identity_20260926T1535/`.

The new `lab/tools/t032_harvest_audit.py` re-executes the exact 39 T028 losses
with official-engine successful SELL hooks. At a conservative material-dump
threshold (MILK/WOOL >=5, STRAWBERRY >=8, MELON >=6), opponents make **1,999**
dumps (18,814 units); **1,603/1,999 (80.2%)** have our successful same-item
sale in t−1/t/t+1, with **1,458** in the same lockstep tick. This establishes
the shared-market timing overlap but not a causal counterfactual.
`runs/t032_harvest_adjacency_20260926T1540/audit.json`.

Fresh, fixed two-world, both-seat screen against the requested non-Horizon
controllers and mirror (Parthenos, MetaV4, Shepherd, es7_wm) is **32/32 valid**.
The forecaster has paired score **0.000pp** (whole-world bootstrap
−12.5…+12.5pp), while paired cash is **+$436.75** (bootstrap +$13.5…+$860).
Cash improves for all four named opponents, but there is no score signal and
only two worlds; it does not satisfy the predeclared clear-score condition.
Therefore T032 is closed: **no T025 full gate, candidate, or Kaggle action**.
`runs/t032_harvest_screen_20260926T1555/`.
