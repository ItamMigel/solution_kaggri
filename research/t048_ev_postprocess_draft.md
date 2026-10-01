# T048 — post-processing over m26: stable plan following + expected future profit (Claude draft), 2026-09-30 10:05Z
Base = t047_m26_terminal (m26dsm + t718 liquidation; candidates/t047_m26_terminal/pkg/main.py). m26 went 128/128 vs our frozen panel,
so every change must be judged HEAD-TO-HEAD vs the base (mirror games are decided by hundreds of $) + sanity vs tetsu/ozer44/parthenos/mix4.
Last useful upload ≈ 18:00 UTC 30.09 (validation + games before 23:59). Container CPU quota 11.5 cores.

## Track A (Claude, now): existing inference flags, zero new logic
- persist=True: keep a unit's target until reached (less target flip-flop between hours).
- dedupe=True: do not send two units to the same (non-shed) target cell.
- persist+dedupe. Gate: 16 new worlds × 2 seats h2h vs base + sanity 8 worlds vs tetsu/ozer44.

## Track B (Codex, research + prototype): expected-value post-processing
B1 Inventory valuation: estimate expected sale value of each product over the remaining days (price curves from official episodes /
   our replays: per product, per day, typical price after town demand; own price impact per unit). Use it to (a) veto BC market SELLs
   that sell far below the expected future price when shed room is not binding, (b) add SELLs when price is above expectation and
   stock is high, (c) plan the last 2-3 days' sell schedule (spread sales across turns/days to limit own price impact; t718 already liquidates).
B2 Market beam / exact scorer: top-K AR decodes of the market head, score by exact own-market execution (engine _process_market,
   same-turn buy→sell, cash) + inventory valuation from B1; pick best; fall back to argmax when scores tie.
B3 Value-weighted fill assignment: replace nearest-first greedy filler with a small assignment over (units with forced PASS) × (tasks)
   using task value (crop/animal product value, starving-animal risk) minus distance; Hungarian exists in lab/re/top_re/units.py.
B4 Anything better: e.g. short Monte-Carlo of own farm economics for land/animal buys, or a frozen-trunk value probe (needs GPU; JH has
   the merged dataset), if it can be gated today.
Deliverable: research/t048_ev_postprocess_codex.md (ranked, with evidence) + the 1-2 most promising variants implemented as default-off
wrappers over the base and gated h2h vs base (16 worlds × 2) + sanity; frozen archives only if PASS (>=65% points, positive margin CI).
