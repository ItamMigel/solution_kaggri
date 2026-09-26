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

Pending.
