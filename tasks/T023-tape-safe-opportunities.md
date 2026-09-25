# T023 — tape-safe idle-unit opportunities

Owner: Codex
Status: in_progress

## Goal
Mine our ladder replays for actions that can safely replace a parent `PASS` without movement, then implement two or three bounded Horizon+ modules and screen them against `es2_c1`.

## Contracts
Each module must preserve default-off action equivalence, target only an observed idle unit, require an immediately legal operation on its current tile, and never change markets, movement, hand count, or another parent unit's command. Frequency is measured before candidate building.

## Method
Analyse `research/census_ours` and `replays/ours` for parent PASS/no-op actions on ready plants/animals/empty owned tiles. Rank by observed occurrence, reward plausibility, and conflict risk. Build composably after `modules.build`, then run a locked paired capability screen with genome0=`es2_c1`.

## Measured candidates
A raw 307-replay scan records historical action/state pairs but its action timing is shifted, so it is not used for selection (`research/t023_tape_safe_mining.md`). A direct sequential execution of frozen `es2_c1` on 16 own ladder replays finds 1,033 residual parent PASS operations (`research/t023_live_sample.md`): WATER 48 (46.5/1k), FEED 10 (9.7/1k), CARE 10 (9.7/1k), HARVEST_ANIMAL 3.

HARVEST_PLANT is deliberately excluded despite 159 observed states: its M1 ablation was catastrophic from early harvest. FERTILIZE is excluded because its prior ablation lost; DIG_WEED has zero observed residual PASS states. The first capability screen therefore tests individual WATER, FEED and CARE only.

## Result
Screen pending.
