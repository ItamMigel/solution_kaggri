# Reverse-engineering top agents (human: full focus until we understand/beat them) — 2026-09-26 18:50Z
Data: replays/top10v4 (~1000 eps of CURRENT top-10 subs, many top-vs-top), replays/reactive (160 eps fuxi/joseph/istinetz/varim), ours_final (es6/es7 ladder).
Tool: lab/re/declog.py → research/re/<team>.jsonl.gz = per-step rows {state: day/hour, me/op farm feats (tiles by crop, ripe yield, animals,
structs, fert tiles, hands, quads, money, hires_today), shed, seeds, carried, prices, market inventory, shops; decisions: market orders, unit-op counts}.
Split: Claude = market + macro rules (SELL item/qty vs price/inventory/stock/day; BUY_LAND; HIRE per day; BUY_ANIMAL/structures; BUY_SEED/PRODUCT).
Codex = production (planting schedule/crop mix per shop set, layout, unit allocation: water/harvest/care/feed/fertilize order).
Method: interpretable rules (thresholds, decision trees) → teacher-forced agreement on held-out episodes → encode as (a) reconstructed agent
"top-RE" for local testing (the missing strong opponent!) and (b) counter-modules / graft candidates on es7_wm. Gate as usual; human submits.
