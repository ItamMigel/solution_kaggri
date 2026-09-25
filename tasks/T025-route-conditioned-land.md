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
