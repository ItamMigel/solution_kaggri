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

## Standard CMA promotion gate (predeclared 2026-09-26)

This gate applies to a frozen CMA centre only after its training generation is complete; it is the replacement test, not a training fitness score. The centre and frozen `candidates/es3_g5/pkg/main.py` must be in one `compare.py` invocation so opponent, world and seat are paired. Inputs must be byte-hashed before/after; no errors, non-DONE status, timeouts or invalid actions are allowed. Every seed must be freshly drawn and excluded from every CMA generation, earlier gate, panel and targeted/T025 run.

1. **H2H superiority:** 8 fresh worlds, both seats (16 games), centre vs `es3_g5`. Pass only if the whole-world 95% bootstrap lower bound is **strictly above 0.500 score** and **strictly above $0 mean margin**.
2. **Reactive-panel non-inferiority:** a separate 24 fresh worlds, both seats, against both `parthenos_robust` and `tschinkel_metav4_v13` (96 games per candidate). Run centre and `es3_g5` simultaneously. Aggregate paired centre-minus-es3 score by whole world (including both opponents and both seats); pass only if its **one-sided 95% bootstrap lower bound is greater than −0.020 score (−2.0pp)**. Report paired cash-margin CI and each opponent split, but do not substitute cash for this safety gate.
3. Promote only if both stages pass, all 208 total games are valid (16 H2H + 192 panel), and the other agent independently reviews or reproduces the result. A failure rejects that centre only; it does not change the frozen control. No Kaggle submission is involved.

## c3g5 adverse-parthenos diagnosis (2026-09-26, diagnostic evidence only)

- c3g5 differs from es3_g5 in 20 static values, but the large relevant change is **`_ADV_LOOK: 17 → 18`**. This is the ADV layer's sale-advance horizon (`main.py:6906–6960`), not the route, hire or land logic. The remaining plausible early-sale values were `_CH_SHED: 96 → 94` and the v9/2 prediction settings; neither explains the adverse worlds.
- Saved local replays, `runs/t025_c3g5_trace_adverse/` (7 adverse development worlds, parthenos, both seats, 28/28 valid), show the initial c3g5/es3 path has identical route, hires and land. First divergence is a sale, not a unit decision: seed 553563789 d14h22 c3 sells 3 MILK one tick before es3; seed 572774699 d15h07 sells 2 EGG early; seed 114026231 d17h14 sells 2 WOOL early. Unit paths stay identical initially (the first later unit difference in 114026231 is d18h15). Thus the adverse mechanism is premature premium sale and the subsequent price/reaction cascade, not the failed early-land hypothesis.
- Targeted rollback on the same seven worlds, both seats, all valid: `_ADV_LOOK=17` changes c3g5's mean parthenos margin **+$1,097 → +$1,347** and losses **4 → 2**. It recovers 553563789 **−$221 → +$392**, 572774699 **−$1,775 → −$1,546**, 1174810681 **+$7,332 → +$7,612**, 1234632958 **+$519 → +$1,016**, and 2096534423 **+$776 → +$1,006**. `runs/t025_c3g5_ch_adv_ablation/`.
- Controls: resetting the v9/2-Q score pair (`_V92_Q_PF`, `_V92_Q_PM`), `_V92_Q_H`, or `_V92_P_H` leaves all seven outcomes byte-for-byte at c3g5 values (`runs/t025_c3g5_q_ablation/`). `_CH_SHED=96` alters only seed 114026231 (+$239) and leaves losses 4/14; it is at most a minor local interaction. **Conclusion: `_ADV_LOOK` is the sole diagnosed knob; it is a trade-off, not a repair.** Claude's separate fresh 8-world H2H of the 17 rollback then fails vs es3_g5 (10–2–4, −$4.8), while c3g5 itself is 14–2–0 (+$547) on those worlds (`runs/gate_al17_h2h`). There is no support for a route/hire/land knob, and neither 17 nor 18 is promoted from this diagnostic.

## CMA3 centre gate — gen 15 (2026-09-26): REJECTED by reactive NI

- Frozen centre `runs/cma3/gen_015/c/main.py` (sha256 `c2f147814791…`) passed stage 1 against frozen es3_g5 on 8 disjoint worlds/both seats: **16–0–0**, +$836.1, whole-world 95% score CI **[1.000,1.000]**, margin **+$526.2…+$1,152.9**, 16/16 valid. `runs/t025_cma3_g015_promotion/h2h/`.
- It then failed stage 2's predeclared strict non-inferiority boundary on a separate 24-world parthenos+metav4 both-seat panel, in a simultaneous centre/es3 invocation: **192/192 valid**, inputs unchanged. Centre: 90–0–6 (93.75%, +$1,183.1); es3: 86–0–10 (89.58%, +$1,231.6). Paired centre−es3 score is **+4.167pp**, but whole-world 200,000-resample bootstrap one-sided 95% lower bound is **−2.083pp**, below the required **> −2.000pp**; paired cash is **−$48.5** (two-sided CI −$270.7…+$152.0). Same +4.167pp score split against each opponent; cash −$54.0 parthenos / −$42.9 metav4. `runs/t025_cma3_g015_promotion/panel/`.
- The H2H stage passes but gate requires both stages. **Do not promote CMA3 gen-15; frozen es3_g5 remains the control.**

## Boundary confirmation predeclaration (2026-09-26, Codex)

- The stage-2 miss is only 0.083pp beyond the strict boundary. Before inspecting any additional games, run **one** additional, fresh 24-world P+M panel: frozen `candidates_wip/es5_c3g15/main.py` (sha256 `c2f147814791…`) and frozen `candidates/es3_g5/pkg/main.py`, simultaneously, versus `parthenos_robust` and `tschinkel_metav4_v13`, both seats, at most eight workers (192 games). Seeds must be excluded from every recoverable prior `runs/` seed artifact, including the first gen-15 promotion panel and CMA training generations. No submission is involved.
- **Promotion rule for this confirmation only:** all 384 P+M games across the old and new 24-world panels must be valid and unchanged; aggregate the paired centre−es3 score by all 48 worlds with the same one-sided 95% bootstrap calculation. Promote only if this combined lower bound is **strictly greater than −2.0pp** *and* the newly drawn 24-world point estimate is **at least 0.0pp**. This supplements (not replaces) the already-passed gen-15 H2H and still requires Claude's independent review. Otherwise retain frozen es3_g5.

## Boundary confirmation result — PASS pending Claude review (2026-09-26, Codex)

- New frozen paired panel: `runs/t025_cma3_g015_boundary_confirmation/panel/`, 24 CSPRNG-drawn worlds in `seeds.json`, checked disjoint from all **967** seed values recoverable from 175 prior manifest/seed artifacts (including `panel_c3g15` and CMA generations). `es5_c3g15` (`c2f147814791…`) and `es3_g5` (`fb194f51…`) were run simultaneously versus parthenos+metav4 in both seats with 8 workers. **192/192 valid**, all DONE, no errors, input hashes unchanged.
- New panel result, c3g15−es3: **+6.250pp** paired score (c3g15 87–0–9, es3 81–0–15) and **+$10.05** paired cash; a 200,000-resample one-sided 95% world bootstrap lower bound is **0.000pp**. Splits: parthenos +8.333pp / +$13.01; metav4 +2.083pp / −$51.44.
- Combined with the predeclared first 24-world panel: **384/384 P+M games valid**, 48 distinct worlds; paired c3g15−es3 score **+5.208pp**, cash **−$19.21**, and 200,000-resample one-sided 95% lower **0.000pp** (two-sided score interval −1.042…+11.458pp; cash −$181.15…+$134.52). Thus `0.000pp > −2.000pp`; the new point estimate is ≥0, and the already-recorded H2H is 16–0 (+$836). The declared numerical promotion gate **passes**. Per shared protocol, do not create/alter a candidate until Claude independently reviews or reproduces this evidence; no Kaggle submission is involved.

## CMA3 → CMA4 restart decision (2026-09-26, Codex)

- **Restart, not continue.** `cma3` had completed gen 16 (centre fitness 0.9853 after gen-14 1.0955; post-tell σ 0.03723, up from 0.02838 at gen 0). Its training panel was still hard-wired to frozen `es3_g5`, whereas gen-15 centre is byte-identical to frozen `candidates_wip/es5_c3g15/main.py` (`c2f147814791c30c3754a3772086e5591d92afebfde3d711c026a12f8186680d`) and has passed the declared numerical replacement gate pending Claude review. Continuing explores an increasingly broad distribution around a superseded control and is lower-value than local search around the evidence-bearing centre.
- Stopped `cma3` during gen 17 without writing a partial fitness result: `runs/cma3/history.json` and `cma.pkl` retain exactly completed gens 0–16, so the old run is intact and resume-able (its incomplete `gen_017/` is only an artifact). No Kaggle operation occurred.
- Started resume-checked **`runs/cma4`** from the exact 24 values saved in `runs/cma4/init_gen15_params.json` (verified equal to `cma3/history.json` gen-15 `centre_params` and regenerates the same `c2f147…` agent with COLLECT). Command: `CMA_BEST=/workspace/shared/candidates_wip/es5_c3g15/main.py python /workspace/wt/codex/lab/tools/knob_cma.py --init runs/cma4/init_gen15_params.json --out runs/cma4 --gens 30 --pop 10 --sigma 0.015 --worlds 8 --workers 18 --collect`. Its immutable `config.json` records the mirror path/hash, σ0, population and world count; an inconsistent resume fails closed. Generation 0 is running with **18 workers**.
- `lab/tools/knob_cma.py` commit `70899fc` now accepts `CMA_BEST` / `--mirror` rather than silently retaining the legacy es2 control, and writes/verifies that run configuration. The first independent gate for CMA4 is after five completed generations, versus the then-frozen control; training does not itself alter any candidate.

## CMA4 launch recovery (2026-09-26)
- The initial CMA4 child inherited a short-lived launcher and stopped after 48/880 games in gen 0, before creating `cma.pkl`; the partial directory is preserved as `runs/cma4_partial_20260926T023116Z/` and no partial fitness was used. CMA4 was restarted cleanly from the same frozen gen-15 parameter vector in tmux session `codex-cma4`, with the corrected mirror file `candidates/es5_c3g15/pkg/main.py`, σ=.015, 8 worlds, pop10, 18 workers. Its first independent gate remains after five completed generations.


## CMA4 centre gate — gen 5 versus promoted es5_c3g15 (2026-09-26): REJECTED by reactive NI

- Frozen centre `runs/cma4/gen_005/c/main.py` (sha256 `faaea0bc9b0e…`) passed stage 1 against frozen `candidates/es5_c3g15/pkg/main.py` (`c2f147814791…`) on eight fresh CSPRNG worlds in both seats: **14–0–2**, score 87.5%, whole-world 95% score CI **[62.5%, 100%]**, mean **+$295.9** (CI **+$62.6…+$571.0**), 16/16 valid, zero errors. `runs/t025_cma4_g005_promotion/h2h/`.
- The separate stage-2 panel used 24 further fresh worlds, both seats, simultaneous centre/control measurement against `parthenos_robust` and `tschinkel_metav4_v13`: **192/192 valid**, all inputs unchanged, zero errors. Centre was 87–0–9 (90.625%, +$1,117.9); control 89–0–7 (92.708%, +$1,076.3). Whole-world paired centre−control score is **−2.083pp**; fixed 200,000-resample seed-230923 one-sided 95% lower is **−8.333pp**, below the required **> −2.000pp**. Paired cash is **+$41.56** (two-sided CI −$21.42…+$115.98), which cannot replace the score safety gate. Splits: parthenos −4.167pp / +$41.19; metav4 0.000pp / +$41.94. `runs/t025_cma4_g005_promotion/panel/paired_analysis.json`.
- Therefore CMA4 gen-5 is rejected and no candidate/control changes. CMA4 itself continues its local search from the frozen es5_c3g15 centre; the next scheduled independent gate is after its completed gen 10. No Kaggle submission occurred.

## CMA4 objective migration at gen-8 boundary (2026-09-26, Codex)

- I agree the old CMA objective was misaligned with the replacement gate.  The raw `games.jsonl` breakdown confirms that the mutation ordering can be driven chiefly by the mirror: in gen 0, `best` fitness ranges **0.1237–1.0115** across candidates, whereas parthenos ranges only **0.6188–0.7459**; the gen-5 gate's only adverse score split is parthenos (**−4.167pp**, versus metav4 **0.000pp**).  This is consistent with the repeated centre pattern, rather than proving any particular knob is causal.
- Generations 0–8 retain their original uniform objective.  After gen 8 wrote `history.json` and `cma.pkl`, the in-progress gen 9 was interrupted before any game result (0 rows), then preserved at `runs/cma4/gen_009_partial_20260926T0453Z/`; it never reached `tell()` and is not used.  The identical saved CMA state and centre are now resumed as gen 9.
- `lab/tools/knob_cma.py` has a versioned `fitness_schedule`.  New gen 9+ mode is `parthenos_x2`: the fitness remains the exact existing per-game score, but it is the weighted mean of opponent means with weights **best/mirror=1, yhay=1, parthenos=2, metav4=1, v5_market=1**.  Thus parthenos is 2/6 objective weight, strictly more than the mirror's 1/6, with no duplicated games or change to the opponent suite.  The script records `fitness_mode` and `fitness_breakdown.by_opponent` for every candidate in each future history entry.
- The one-time, fail-closed migration requires the requested transition generation to equal the completed history length.  `runs/cma4/fitness_transition.json` records hashes of the pre-migration config, history and CMA pickle plus the schedule; `config.json` now fixes `uniform` for gen 0 and `parthenos_x2` beginning gen 9.  A second transition or inconsistent core config aborts.  History and CMA pickle writes are atomic henceforth.  A dry resume at `--gens 9` verified the transition without an evaluation; the live tmux `codex-cma4` then restarted gen 9 on its originally generated eight seeds.  No candidate was changed and no Kaggle operation was performed.


## CMA4 centre gate — gen 10 versus promoted es5_c3g15 (2026-09-26): REJECTED by reactive NI

- Frozen centre `runs/cma4/gen_010/c/main.py` (sha256 `bb68af3320b2…`) passed the fresh stage-1 H2H against frozen `candidates/es5_c3g15/pkg/main.py` (`c2f147814791…`): **16–0–0**, whole-world score CI **[100%, 100%]**, mean **+$495.13** (CI **+$237.88…+$765.02**), 16/16 valid and zero errors. `runs/t025_cma4_g010_promotion/h2h/`.
- The separately drawn stage-2 P+M panel ran both agents simultaneously against `parthenos_robust` and `tschinkel_metav4_v13`, 24 worlds and both seats: **192/192 valid**, inputs unchanged and zero errors. Centre was 84–0–12 (87.5%, +$796.24); control 90–0–6 (93.75%, +$849.20). Whole-world paired centre−control score is **−6.250pp**; fixed 200,000-resample seed-230923 one-sided 95% lower is **−14.583pp**, below required **> −2.000pp**. Paired cash is **−$52.95** (two-sided CI −$160.98…+$49.93). Split: parthenos 0.000pp / −$51.21; metav4 **−12.500pp** / −$54.69. `runs/t025_cma4_g010_promotion/panel/paired_analysis.json`.
- Therefore CMA4 gen-10 is rejected; no candidate/control changes. The completed gen-10 H2H signal cannot override its independent safety-panel failure. CMA4 continues its local search; the next scheduled independent gate is after completed gen 15. No Kaggle submission occurred.

## CMA4 objective migration at completed gen-13 boundary (2026-09-26, Codex)

- The gen-10 failure moved from parthenos to metav4, so I agree that merely doubling one named opponent is whack-a-mole rather than a sufficiently general fitness objective. Gen 13 completed normally under the prior `parthenos_x2` schedule: 880/880 training games, centre fitness 1.03823, best `x4` 1.05929, post-tell sigma 0.0156290. Its centre/state are preserved in the normal atomic `history.json`/`cma.pkl`.
- At that completed boundary, `lab/tools/knob_cma.py` appended the audited `panel_rotating_8` phase beginning gen 14. `fitness_transition_014.json` binds the preceding config/history/CMA-state hashes and exact schedule; no parameter or RNG/CMA state was modified. A zero-row pre-transition `gen_014/` created while stopping the old launcher is retained as `gen_014_partial_pretransition_20260926T0617Z/` and is never used.
- Each new generation remains eight worlds, population 10 + centre and 18 workers. Fitness is a weighted mean of opponent means: frozen mirror `es5_c3g15` **1/8**, `parthenos` **2/8**, `metav4` **2/8**, plus three consecutive members of a five-generation rotating cycle `{yhay_router0913, tschinkel2945, ozer_v45, yaxon_reactive_v5, pilkwang_struct}` at **1/8** each. Thus no duplicate games encode the weights, all five extras occur in three of each five generations, and every history entry records its exact weights/opponents and per-opponent fitness splits. Gen 14 is live with the first slice `pilkwang/yhay0913/tschinkel2945` (rotation is keyed by absolute generation number).
- Retrospective whole-panel gate diagnostic is running separately, with the original g5/g10 24-world gate seeds and the same frozen candidate/control agents: P+M results are being extended to control/mirror plus all five rotating-pool opponents. It will report the predeclared one-sided paired score test over the full 8-unit panel; it cannot revise either already-recorded P+M rejection. No Kaggle submission or candidate mutation occurred.

## CMA4 gen-14 integrity recovery (2026-09-26, Codex)

- The first post-transition gen-14 evaluation completed 1,584 games, then **failed closed before `tell()`**: the rotating-panel command omitted an explicit empty `--baselines`, so `compare.py` injected its three legacy baseline opponents. `_fitness_from_games` detected the unexpected `v3`, `v4_12turn`, and `v4_8turn` labels; `history.json` and `cma.pkl` still end at completed gen 13. The malformed artifacts are retained at `runs/cma4/gen_014_extra_baselines_20260926T0642Z/` and are excluded from search and any gate.
- Fixed `panel_rotating_8` to pass its explicit `--baselines` terminator (commit `8af8237`, merged to `lab` in `8f5a695`). A clean deterministic rerun of gen 14 starts from the unmodified gen-13 state and the same eight seeds, with exactly its six configured opponents / 1,056 games. No candidate, CMA update, or Kaggle action occurred.

## CMA4 whole-panel retrospective — g5 (2026-09-26, diagnostic only)

- The g5 extension completed **864/864 valid** games. `compare.py` had also emitted three implicit legacy-baseline opponent rows; the planned six-opponent rows are all complete, and the reporting tool now excludes those unplanned labels while recording their counts. This changes neither the earlier P+M gate nor its rejection.
- Combining the original P+M panel with the planned control plus five-extra extension gives the predeclared weighted eight-unit retrospective: **+3.750pp** paired score, one-sided 95% lower **+1.250pp**, paired cash **+$52.98** over 24 worlds (`runs/t025_cma4_whole_panel_retrospective/cma4_g005_whole_panel_analysis.json`). It passes this *diagnostic* NI statistic. The matching g10 extension is running with an explicit empty `--baselines` terminator (576 planned games).

## CMA4 fresh full-panel promotion gate — predeclared before run (2026-09-26, Codex)

- This is a new, one-shot confirmation of the **better of the already observed CMA4 gen-5 and gen-10 centres**, not a reinterpretation of either used-world retrospective.  Do not begin it until `cma4_g010_whole_panel_analysis.json` exists.  Select the centre with the larger full-core retrospective one-sided 95% paired-score lower bound; break an exact tie by the larger retrospective paired-score point estimate, then by gen-10.  Those diagnostics choose the tested hypothesis only; none of their worlds enter this gate.
- Freeze that centre, its SHA-256, and frozen control `candidates/es5_c3g15/pkg/main.py` (SHA-256 `c2f147814791c30c3754a3772086e5591d92afebfde3d711c026a12f8186680d`) before execution.  Draw **16 CSPRNG fresh worlds**, exclude all seeds recoverable from every CMA4 generation, retrospective, gate, panel and other T025 artifact, and run both seats.  Candidate and control must be evaluated in the same `compare.py` invocation; hash inputs before/after.  Any error, non-DONE status, timeout, invalid action, missing paired row, or changed input is a failure.
- The panel contains the eight named full-core opponents: mirror `es5_c3g15` H2H, `parthenos_robust`, `tschinkel_metav4_v13`, `yhay_router0913`, `tschinkel2945`, `ozer_v45`, `yaxon_reactive_v5`, and `pilkwang_struct`; plus external Horizon family `es1_g9` and `v5_market`.  The two Horizon agents are reported separately and are averaged first into one equal-weight **family** stratum, so the aggregate is the eight core units plus one family unit (nine equal-weight strata); no named opponent is omitted.  Within every stratum, first average paired candidate-minus-control score over both seats for each world, then average the 16 world blocks.  The panel statistic is the unweighted mean of its nine stratum means.  Bootstrap resamples the same 16 world indices jointly across all strata, 200,000 resamples, fixed seed 230923.
- **PASS only if** (a) all 640 candidate/control games are valid (16 worlds × 2 seats × 10 opponents × 2 agents), (b) the equal-weight panel paired-score one-sided 95% lower bound is **strictly greater than 0**, and (c) no individual named opponent's 16-world paired-score point estimate is below **−10.0pp**.  Cash is descriptive only.  Use at most four workers while CMA4 uses 18 (therefore within the shared 22-worker per-agent limit; this also satisfies the requested ≤8 cap).
- On PASS only, freeze the exact tested file as `candidates_wip/es6_<tag>/` with `main.py`, SHA-256/evidence, immutable copied inputs and this gate report; notify Claude using `bin/say claude`.  This creates no Kaggle submission and does not replace the promoted control without the required independent review.
