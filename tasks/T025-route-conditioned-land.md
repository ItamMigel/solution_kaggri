# T025 — Route-conditioned early SW-land + CMA centre gates (owner: codex, 2026-09-25)

## Goal
Use T024 ladder evidence to condition the existing debt-confirmed early land macro on a reproducible route/shop signal, build it as an isolated composable layer over `modules.build` / es2_c1, then use `race.py` capability → race gates against genome0 es2_c1.

Every five completed CMA2 generations, independently gate the stored centre against the current champion. After Claude's 2026-09-25 instruction this is frozen `candidates/es3_g5/pkg/main.py` (previous gen-5/10/15 signals used es2_c1) on 8 fresh worlds in both seats.

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

## CMA2 centre gate — gen 10
- Centre `runs/cma2/gen_010/c/main.py` (sha256 `dddf810e…`) vs frozen es2_c1 on eight new worlds, both seats: **14–0–2** (87.5%; world-score CI **62.5…100%**), mean **+$418.0** (world-margin CI −$53.8…+$1,015.6), zero errors. Run: `runs/t025_cma2_g010_gate/arena/`; seeds are stored alongside it. This is the required periodic signal, not an automatic promotion. The two losses are the same BRUNCH_SPOT world in opposite seats (−$667 each). Next independent gate is due after CMA2 gen 15.

## CMA2 centre gate — gen 15
- Centre `runs/cma2/gen_015/c/main.py` (sha256 `8405f56f…`) vs frozen es2_c1 on eight newly drawn worlds, both seats: **14–0–2** (87.5%; whole-world score CI **62.5…100%**), mean **+$493.9** (whole-world margin CI +$166.6…+$839.3), worst −$76, zero errors. Run: `runs/t025_cma2_g015_gate/arena/`; seeds alongside it. The generic harness also ran its default legacy comparators (all wins), but the recorded gate result is the predeclared es2_c1 pair. This is a periodic signal only, not an automatic promotion.

## Control-opponent update
- 2026-09-25: Claude designated promoted `es3_g5` as the gate opponent. Starting at gen 20, centres are measured versus that candidate rather than es2_c1; the earlier es2_c1 signals remain historical and are not comparable promotion evidence.

## CMA2 centre gate — gen 20 (new champion control)
- Centre `runs/cma2/gen_020/c/main.py` (sha256 `cd1b7ee7…`) vs promoted frozen `es3_g5` on eight newly drawn worlds, both seats: **3–0–13** (18.75%; whole-world score CI **0…43.75%**), mean **−$349.9** (whole-world margin CI **−$702.5…−$100.1**), worst −$1,439, zero errors. Run: `runs/t025_cma2_g020_vs_es3g5_gate/arena/`. Clear rejection versus the actual current control; do not promote this centre. Next scheduled signal is after gen 25.

## CMA3 handoff
- 2026-09-25: Claude stopped CMA2 after the gen-20 rejection and launched `runs/cma3` from promoted es3_g5 parameters (`sigma=0.03`, es3_g5 mirror control). The scheduled independent gates now apply to CMA3 centres versus frozen es3_g5 every five completed generations. First gate: after gen 5.

## CMA3 centre gate — gen 5
- Claude's first gate (`runs/gate_cma3_g5`) recorded 15–0–1 versus es3_g5 on eight fresh worlds (+$978.9, score CI 81.25…100%, one −$2,377 loss). Codex independently used eight different fresh worlds, both seats: `runs/cma3/gen_005/c/main.py` (sha256 `9c93abe2…`) scored **14–0–2** against frozen es3_g5 (87.5%; whole-world score CI **62.5…100%**), mean **+$558.2** (whole-world margin CI +$125.0…+$1,288.5), worst −$14, zero errors. Run: `runs/t025_cma3_g005_independent_gate/arena/`. This corroborates the gen-5 centre signal but is not an automatic promotion; next scheduled independent signal is after CMA3 gen 10.

## T025 follow-up claimed — c3g5 targeted red-team + CMA3 gen-10 gate (2026-09-25, Codex)
- Before running, Codex will freeze two disjoint fresh seed files and exclude every seed recoverable from `runs/panel_c3g5` and prior `runs/*gate*` / T025 output. Current CMA3 training consumes 18 workers, so these two jobs use four workers total (≤22). No Kaggle submission is involved.

## Targeted c3g5 red-team — 24 fresh worlds, parthenos + metav4 (2026-09-26, Codex)
- Frozen inputs: `candidates_wip/es4_c3g5/main.py` (`9c93abe2…`) and `candidates/es3_g5/pkg/main.py` (`fb194f51…`), versus `parthenos_robust` and `tschinkel_metav4_v13`; seeds `runs/t025_c3g5_targeted_parthenos/seeds.json` were checked disjoint from all prior seed-bearing `runs/` artifacts, including `panel_c3g5` and earlier gates. Command used local `/workspace/wt/codex/compare.py`, both seats, four workers while CMA3 used 18. **192/192 valid, zero errors, input hashes unchanged.**
- c3g5: parthenos **37–0–11**, +$818.5; metav4 **45–0–3**, +$1,293.5. es3_g5: parthenos **39–0–9**, +$896.8; metav4 **47–0–1**, +$1,353.7. Thus c3g5−es3_g5 is **−4.17pp** paired score (whole-world bootstrap [−10.42, 0]pp) and **−$69.25** margin (CI [−$176.65, +$33.30]) across the fixed suite — no superiority and a directionally adverse parthenos replication. **Do not promote es4_c3g5.**
- Per-world paired margin differences c3g5−es3_g5 (average of both seats; `$`; score delta is zero except P:553563789 and M:944686768, each −1):

| seed | parthenos | metav4 |
|---:|---:|---:|
| 114026231 | −165 | −133 |
| 173784933 | −26 | +148 |
| 371944795 | +272 | +390 |
| 389532716 | −114 | +640 |
| 553563789 | −543 | −192 |
| 558688507 | −118 | +380 |
| 572774699 | −672 | −991 |
| 623936053 | −7 | −159 |
| 696981031 | +56 | +347 |
| 944686768 | −6 | −206 |
| 966644471 | −9 | +12 |
| 1021258629 | −102 | −100 |
| 1114820177 | +290 | +289 |
| 1161890718 | −171 | +60 |
| 1174810681 | −278 | −391 |
| 1218191577 | +129 | −699 |
| 1234632958 | −469 | −423 |
| 1346881843 | −39 | −30 |
| 1551672846 | −8 | +1 |
| 1636040957 | +333 | +202 |
| 1663903600 | +125 | −392 |
| 1763925789 | −92 | +82 |
| 2096534423 | −230 | −291 |
| 2128588532 | −37 | +12 |

## CMA3 centre gate — gen 10 (2026-09-26, Codex)
- On eight other fresh worlds (`runs/t025_cma3_g010_gate/seeds.json`), both seats, frozen `runs/cma3/gen_010/c/main.py` (`bd43a6ca…`) and c3g5 were each measured against frozen es3_g5 in the same `compare.py` invocation: **32/32 valid, zero errors, inputs unchanged**.
- CMA3 gen-10 vs es3_g5: **15–0–1**, 93.75%, +$437.4 mean margin (world score CI 81.25…100%; margin CI +$136.4…+$955.3). c3g5 on exactly that panel: **15–0–1**, +$386.9. Direct CMA3−c3g5 paired result: **0.00pp** (CI [0,0]) and **+$50.5** margin (CI [−$39.25,+$132.0]); seed averages: 142428386 +235, 500621362 +145, 737697958 +60, 764089769 +1, 1234645335 0, 1329740717 0, 1820563819 +151, 1938237547 −188. So gen-10 does **not** establish a beat over c3g5; it is only a positive signal over es3_g5, pending independent confirmation before any promotion.
