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

## Codex M4 capability result — 2026-09-24 22:15 UTC
- All 120 games valid. Only `room_guard_on` has a positive paired score signal vs byte-identical genome0: **+0.2500** (whole-world CI [0,+0.25]), +$19.5 (CI +$16…+$23) over two fresh worlds against g9+yhay0913. It advances to the disjoint 4-world race.
- Reject: `hand_align_off` −0.75 / −$43,956; `budget_guard_on` −0.25 / −$97.5; `opening_12` −0.25. No signal: clamp/dead-stock/front-run/terminal/weed off/opening5/router672. FD708 and router624 are uncertain (score CI crosses 0); `sell_lead_off` uncertain. Evidence: `runs/hplus_m4_capability/eval/{PAIRED.md,compare/}`.

## Codex M4 race result — 2026-09-24 22:20 UTC
- `room_guard_on` did **not** reproduce on its disjoint 4-world race against g9/v5_market/yhay0913: paired score **0.0000**, CI [−.125,+.125], margin −$4.8, CI [−$20.2,+$6.0], 48/48 valid. No M4 flag advances to final/CMA. Evidence: `runs/hplus_m4_race/eval/{PAIRED.md,compare/}`.
- M1 ablation (192 games, 8 worlds): vs g9 COLLECT 13-3 (+$20), harvA 10-6 (+31 but worst10 −674), CARE/WATER ≈ never fire, FERTILIZE 2-14, HARVEST_PLANT 0-16 (−1.4k, early harvest kills the watering bonus). → race on a locked fresh fold (codex race.py, stage race: 4 worlds × g9/v5/parthenos × seats): genome0, collect, harvA, collect+harvA → runs/hplus_m1_race.
- Codex (T020) found PPO warm-up bug (value loss moved shared trunk → approx_kl .75 at iter 0); fixed in lab 7c2c1e2. H100 package rebuilt as **v2.1** (same path, new sha256 e98ac33f…), hotfix file h100_pkg/ppo_v2.1_hotfix.py.
- Codex M4 builder (lab/hplus/config.py) + race harness (lab/hplus/race.py) ready; M4 capability screen running (runs/hplus_m4_capability).
- M1 race (fresh fold): collect +0.167 / +$22 [+1,+43] survives; harvA & collect+harvA negative → dropped. Final stage (8 worlds × 5 opp) for collect running → runs/hplus_collect_final. Codex: M4 flags all inert/negative on disjoint race (room_guard didn't reproduce) → M4 closed.

## M3lite fertilizer-hand — claimed by Codex 2026-09-24
- Separate composable default-off builder after `modules.build`; scope is one appended hired hand only, with explicit order-slot, affordability, index-stability and daily lifecycle checks before any arena screen.
- collect FINAL stage (8 worlds × 5 opp): paired +0.0875 [+0.06,+0.10], vs g9 15-1 (genome0 1-14-1), no regression elsewhere. Candidate es2_c1 = g9+collect → promotion gate (16 fresh worlds vs g9, g1, v5×2) runs/gate_es2_c1.

## Codex M3lite trace and safety gate — 2026-09-24
- First deliberately aggressive two-world smoke (`fh_day0=0`, `fh_day1=28`, no cash reserve) was reproducibly harmful: paired score −0.5000 / −$2,972 vs g9, 0 errors. Replays `runs/hplus_fh_trace/` locate first divergence at step 147/day 6: g9 had $993, 9 hires today and 1 shed fertilizer; the wrapper appended a 10th HIRE, then consumed it. That cannibalised the parent's future fertilizer sale path and cascaded into the loss. It is rejected, not screened further.
- Hardened contract landed in lab (`e0c959f`, merge `890e3cf`): configurable fertilizer reserve (default 6), max parent hires before append (default 5), and abstention on a parent fertilizer market/pickup/place operation or parent fertilize target. It also requires the reserve both before HIRE and before appended PICKUP. Build/validation/config tests: 7/7 pass.
- Fresh locked two-world capability smoke of safe enabled defaults vs g9+yhay0913: **8/8 valid**, paired score **0.0000** and margin **$0.0** exactly. Evidence `runs/hplus_fh_safe_capability/`; this validates non-interference but is intentionally inert, not a candidate. Next: find an observed high-surplus firing regime before a new screen.
