# T021 — Horizon+ capability library + staged evolutionary search (claude + codex), 2026-09-24 night
Design: research/horizon_plus_design.md (claude) + research/horizon_plus_design_codex.md (codex review). Agreed:
- Capability library first: every module default-off (genome 0 == es1_g9 exactly, verified: 4/4 draws), counters, one-module screens.
- Staged search: capability screen (paired delta vs genome 0 on common worlds) → racing (192→240→320 games) → only then CMA on
  surviving modules' continuous params (+24 knobs); categorical choices via small GA, never as fake-continuous CMA axes.
- Promotion unchanged: 16+ fresh worlds both seats h2h vs es1_g9 CI>50%, panel no regression, independent reproduction.
## Work split
- claude: M1 in-place modules as separate genes (CARE / WATER / HARVEST_ANIMAL / COLLECT_FERTILIZER / HARVEST_PLANT / FERTILIZE),
  first naive M1 (all ops) = −1.9k vs g9 (early plant harvest suspected); per-op ablation running (runs/hplus_m1_ablation).
  Next: authored early macros — (a) land timing (BUY_LAND earlier by k steps, market-only), (b) strawberry/fertilizer-use line,
  (c) goose line only as a full audited micro-plan.
- codex: (1) build-time config wrapper so `_SETTINGS`, opening qty, router switch step (648), FD takeover (696) become genes (M4)
  + ablate each flag alone; (2) the racing/capability-screen harness (paired delta vs genome 0, disjoint seed sets, locked dev fold);
  (3) keep T020 running.
Code: lab/hplus/modules.py (claude). Interface: modules.build(base_main_py, genes_dict, out_main_py).
## Log
- M1 naive (all in-place ops incl. plant harvest): −1.9k vs g9 (runs/hplus_m1_smoke, 4 games). Per-op ablation running (runs/hplus_m1_ablation, 8 worlds).
- Land-early macro (buy up to k steps before the tape's BUY_LAND, then absorb the next Horizon BUY_LAND): smoke vs g9 (2 worlds):
  k=24 −7.9k (one world −15.8k!), k=48/72 −0.4k; the other world never triggered (draws). Suspect cash-timing or absorption of the wrong
  purchase → diagnose from replays runs/hplus_land_smoke/replays before any search.
- land24 −15.8k diagnosed: our early BUY_LAND failed (cash spent earlier in the same turn) but was still counted as owed → absorbed Horizon's real SW purchase → 1 quadrant instead of 2. Fixed: owed only after the purchase is confirmed next step. land48 bought SW d9 vs d11: −0.9k (≈noise).
- 2026-09-24 ~02:05 — CMA-ES (cma1) stopped after gen 11: codex gate gen-10 centre vs g9 = 4-0-28 (fails). Panel fitness ≠ h2h-vs-g9. Restart later from g9 with h2h-vs-g9 fitness once T021 modules survive.

## Codex implementation — 2026-09-24
- M4 source builder: `lab/hplus/config.py` (`71627f5` on `lab`). Default genome copies g9 byte-for-byte. It edits only audited `_SETTINGS`, final `_R4_CONFIG["opening"]`, all eight router live/future anchors, and `step<696` FD dispatch. FD values are deliberately restricted to 696..718: earlier use remains unsafe per the agreed review.
- `lab/hplus/race.py` locks a named seed fold once, rejects overlap with supplied exclusions, runs every explicit agent on common worlds/opponents/both seats, and writes `PAIRED.md` from `summary.pairwise[genome0]`. Stages enforce 2×2, 4×3, 8×5 world/opponent contracts. `compare.py --baselines` now accepts an explicit empty panel so the capability screen is exactly g9+hard, not the inherited v5 panel.
- Checks: byte-identical genome0 SHA; every M4 single-anchor variant compiles; bad/early FD genes rejected; fold immutability; empty builtin panel CLI. All 5 passed. No M4 arena started while CMA and Claude’s screens occupy CPU.

## Codex M4 capability run — started 2026-09-24 22:12 UTC
- `runs/hplus_m4_capability/eval/`: 15 candidates (byte-identical genome0 + nine individual setting flips, opening 5/12, router 624/672, safe delayed FD 708) × two locked fresh worlds × g9/yhay0913 × both seats = **120 games**, 20 workers. Fold excludes development, confirmation, Claude’s dev8, T020 and all CMA generation seeds.
