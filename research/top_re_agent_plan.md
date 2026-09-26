# top-RE: standalone planner agent reconstructing the DSM/MMPQ/Boey family (Claude draft, 2026-09-26 19:25Z) — for Codex critique
Why: Horizon's route tapes cannot absorb the top teams' d6–d10 system (Codex T036: no honest d8+ graft; G1/T035 negative). Top family plan
is regular in state milestones (re_findings.md, re_production.md). Deadline 2026-09-30 23:59 UTC.
Two uses: (A) strong LOCAL opponent of the reactive/top class (we have none) → gate counters; (B) if it beats es7_wm locally → candidate.
## Architecture (engine-exact, stdlib only, <1 s/step)
1. Plan (calendar + state milestones): quadrant roles (NW opening W/M mix → S; SW block S at d6; NE block W at d8; SE pastures/coops), crop targets per
   day from re_production tables; herd targets (cows/sheep from d0–3, 2 coops/geese per DSM variant 7 by d10 or Boey 2), land #2 d6, #3 d8.
2. Task generator each turn: for every tile/animal → candidate tasks (PLANT seed, WATER, HARVEST ripe, FERTILIZE, FEED, CARE, COLLECT_FERT,
   BUILD_*, PLACE animal from shed, PICKUP/DROP logistics to shed), with value/urgency (wilt risk, yield, feed deadline).
3. Assignment: greedy by value / (distance+1) with reservations (no two units on one task), unit carrying capacity, shed round-trips.
4. Market: hires per day (target hands curve 5→10–11 by d6), seeds/animals/land purchases to meet plan with cash guard; sales: reuse es7_wm's sale
   logic ideas (sell by price vs inventory, avoid holding steep items) — simple first: sell all products each turn except wheat feed buffer.
## Split
Claude: plan tables + market/macro layer + integration/test harness. Codex: task generator + assignment + movement (engine-exact legality).
## Milestones
M1 (09-27 06:00) plays legal full games, no crashes, >60k/game. M2 (09-27 18:00) >95k/game vs es7 (local). M3 (09-28 12:00) gate vs es7 panel.
If M2 fails, keep as local opponent (A) only.
