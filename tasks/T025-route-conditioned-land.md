# T025 — Route-conditioned early SW-land + CMA centre gates (owner: codex, 2026-09-25)

## Goal
Use T024 ladder evidence to condition the existing debt-confirmed early land macro on a reproducible route/shop signal, build it as an isolated composable layer over `modules.build` / es2_c1, then use `race.py` capability → race gates against genome0 es2_c1.

Every five completed CMA2 generations, independently gate the stored centre against `candidates/es2_c1/pkg/main.py` on 8 fresh worlds in both seats.

## Constraints
- Kaggle read-only; never submit.
- Claude CMA2 uses 18 workers. Codex uses at most 16 workers.
- Do not repeat the already failed unconditional early-land macro.

## Started
- Gen-5 centre h2h and route/shop condition extraction started.

## Route condition and capability result
- All five repeated T024 Motoki/Koba losses had no `YARN_STORE` among the first two shops. That is exactly router expert `EXP240`; the wrapper only calls the existing confirmed-debt `_hp_land` helper after that router choice, for the second quadrant only, and continues solely long enough to absorb its owed parent land. It cannot accelerate third land.
- `lab/hplus/route_land.py` (commit `1469eb3`, merged to `lab`) is a distinct namespace layer over promoted es2_c1. It evaluated lead 48 and 72 steps (targeting d9/d8 from baseline d11), buffer $300. Twelve isolated-wrapper/config tests pass.
- Fresh locked 2-world capability, g9+yhay, both seats: 24/24 valid. Both variants were identical: versus g9 2–0–2, mean −$1,876, while genome0 es2_c1 was 4–0–0, +$25; versus yhay candidate +$3,060 vs genome0 +$4,550. Paired candidate delta is −0.25 score / −$1,695 (CI [−.50,0]/[−$3,390,0]). **No race.**

## CMA2 centre gate — gen 5
- Centre `runs/cma2/gen_005/c/main.py` vs frozen es2_c1 on 8 fresh excluded worlds, both seats: **15–0–1**, +$281.4 mean margin, world CI +$157…+$395, zero errors. This validates the requested periodic h2h signal only; it does not promote a CMA centre. Next independent gate is due when CMA2 completes gen 10.
