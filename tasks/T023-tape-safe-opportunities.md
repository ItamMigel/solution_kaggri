# T023 — tape-safe idle-unit opportunities

Owner: Codex
Status: in_progress

## Goal
Mine our ladder replays for actions that can safely replace a parent `PASS` without movement, then implement two or three bounded Horizon+ modules and screen them against `es2_c1`.

## Contracts
Each module must preserve default-off action equivalence, target only an observed idle unit, require an immediately legal operation on its current tile, and never change markets, movement, hand count, or another parent unit's command. Frequency is measured before candidate building.

## Method
Analyse `research/census_ours` and `replays/ours` for parent PASS/no-op actions on ready plants/animals/empty owned tiles. Rank by observed occurrence, reward plausibility, and conflict risk. Build composably after `modules.build`, then run a locked paired capability screen with genome0=`es2_c1`.

## Result
Pending.
