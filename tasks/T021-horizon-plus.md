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
