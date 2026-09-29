# Kaggriculture — current public notebook agents (snapshot 2026-09-28)

Read-only Kaggle research. Nothing was submitted or pushed. Every agent was extracted statically, without executing any notebook code, and then safety-scanned before it was run.

## How the data was collected
- **Kernel list:** the Kaggle API returned 608 competition-scoped kernels, sorted by dateRun (`raw/` and `kernels.json`).
- **"current search score":** the SDK search field `best_public_score`, which is the same field that `fetch_top_kernel_scores.py` reports. I pulled it with one bulk search query over the competition, not with 608 lookups, one per kernel.
- **"best public (ver)":** Kaggle's `bestSubmissionScore` from the kernel view model. It gives the best public score of any version of the kernel and names the version that scored it. `kernel_archive.py` computes the same thing. Per-version score lists for 19 kernels are in `raw/version_scores*.json`.
- **Selection (36 kernels):**
  - A: the top 15 by current search score.
  - B: every kernel run on or after 2026-09-24 whose best-version score is >= 2500.
  - C: 8 extra September kernels with a best version >= 2736 that were not already known.
- **Download:** for each selected kernel, the source of its best-scoring version (`archive/<owner>__<slug>/vNNN__scriptVersionId-*/`).
- **Extraction:** `tools/static_extract.py` and `tools/extract_all.py` decode `%%writefile`, `b''.join` literals, base64/b85 + zlib/gzip/lzma payloads, embedded tars, FILES dicts, and one custom lzma container. Each agent is written to `agents/<owner>__<slug>/`.
- **Safety check:** `tools/safety_scan.py` runs an AST scan over each agent and recursively decodes and scans every embedded or `exec`'d source.
  - No agent imports subprocess, socket, urllib, http, requests, shutil, pickle, ctypes or multiprocessing.
  - No agent writes files or uses `os.system`.
  - The only file reads are the agent's own `actions.json` / `settings.json`.
  - One `os.environ.get("V92_SELL_LIB")` (unset, so no read), in the Metav4-family files.
  - `importlib` is used only to load sibling files in kaggricult-man.
  - All 36 agents are marked safe.
- **Smoke test:** `tools/smoke.py` runs `solution/game_worker.py`, candidate in seat 0 against `horizon_v5_market`, seeds 11 and 12, 6 processes, with cwd set to the agent folder. There are 32 unique main.py files, and 4 kernels are byte-identical to one of them (the result is copied for those). Results are in `smoke_results.json`. All 64 games reached DONE/DONE with 719 calls and no errors.
- **Behaviour profiles:** `tools/profile_game.py` covers 13 representative agents × 2 seeds, with v5_market recorded in every game. Results are in `raw/behaviour_summary.json` and `raw/profiles/`.

**Asset notes:**
- Multi-file agents:
  - `leoprovorov__kaggricult-man-reverse-engineering`: 7 .py files + `actions.json` 5 MB + `settings.json`.
  - `guruprasaathas111__kaggriculture-master-engine-v3`: `main.py` + `actions.json`.
  - `leoprovorov__god-s-mode-hacked-stores`: `main.py` imports `base_agent`, `shop_overlay`, `shop_predictor`.
- Paths are resolved from `__code__.co_filename`/`sys.path` at load time, so the multi-file agents run with any cwd.
- god-s-mode uses plain module names, so two god-s-mode instances in one process would collide.
- Everything else is a single-file `main.py`.

## Table (all 36 selected kernels)
| # | grp | kernel (best ver) | author | last run | best public (ver, ver date) | current search score | runnable | vs v5_market s11 / s12 (margin $) | max ms | known? | lineage | strategy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | A | [ahmedberatozer/kaggriculture-v38-smarter-feed-stronger-margins](https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v38-smarter-feed-stronger-margins) v1 | Ahmed Berat Özer | 2026-09-12 | 2625.2 (v1, 2026-09-12) | 2625.2 | yes | -3,944 / -6,652 (W 0/2) | 172 | new (older sibling of pool/ozer_v43) | Ozer V-series chassis: tschinkel runtime + yhay81 shop-router tapes + prvsiyan V221B/V224C + aurax7 storage guard + Gluzdov terminal rescue | 13 shop-route tapes; production-value feed skipping, protected surplus-fertilizer sales |
| 2 | A | [ahmedberatozer/kaggriculture-v39-ready-before-the-rush](https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v39-ready-before-the-rush) v1 | Ahmed Berat Özer | 2026-09-13 | 2626.8 (v1, 2026-09-12) | 2621.2 | yes | -3,789 / -6,585 (W 0/2) | 136 | new (= master-engine-v53e01d74d8f) | Ozer V-series (V38+) | production-calendar feeding, bounded wheat replenishment, stock reserved before full-queue turns; cash-funded purchases only |
| 3 | A | [ahmedberatozer/kaggriculture-v34-observed-market-timing](https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v34-observed-market-timing) v1 | Ahmed Berat Özer | 2026-09-11 | 2601.6 (v1, 2026-09-10) | 2601.6 | yes | -7,152 / -9,570 (W 0/2) | 114 | new | Ozer V-series (V33+); lucifer19 Harvest Nocturne reservations | price-loss ordering inside sale blocks; 3-turn reservations gated by rival-tile similarity |
| 4 | A | [ahmedberatozer/kaggriculture-v53-opening-signature](https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v53-opening-signature) v3 | Ahmed Berat Özer | 2026-09-20 | 2597.5 (v3, 2026-09-20) | 2597.5 | yes | -1,267 / -1,463 (W 0/2) | 639 | new | Ozer V52 + Metav4 v9 layers (RACE/_V92) + Pipe16/Gluzdov sale streams | opponent-sale forecaster keyed on step-2 wheat opening signature; V52 farm unchanged |
| 5 | A | [ahmedberatozer/kaggriculture-v55-one-turn-market-race-edge](https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v55-one-turn-market-race-edge) v1 | Ahmed Berat Özer | 2026-09-21 | 2595.8 (v1, 2026-09-21) | 2595.8 | yes | -1,995 / -1,534 (W 0/2) | 253 | new | Pipe-16 HybridOpening + Metav4 (V54) ; Ozer | V54 + premium-sale reservation horizon 40->41 turns (same-demand race vs Frontier clones) |
| 6 | A | [ahmedberatozer/kaggriculture-v41-review-candidate](https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v41-review-candidate) v1 | Ahmed Berat Özer | 2026-09-13 | 2622.4 (v1, 2026-09-13) | 2586.4 | yes | -3,787 / -6,583 (W 0/2) | 156 | new | Ozer V39 + Rayk Kretzschmar opening | V39 with funded atomic opening |
| 7 | A | [leoprovorov/kaggricult-man-reverse-engineering](https://www.kaggle.com/code/leoprovorov/kaggricult-man-reverse-engineering) v1 | AlekseiProvorov | 2026-09-26 | 2583.6 (v1, 2026-09-10) | 2579.4 | yes | -3,984 / -8,945 (W 0/2) | 112 | new | Dmitrii Gluzdov Seven-Turn Rescue T4; multi-file (importlib) + 5 MB actions.json route tapes | public route-tape replay + adaptive T-1/T-2 inventory pre-emption + terminal value guard |
| 8 | A | [ahmedberatozer/kaggriculture-v31-production-and-sale-priority](https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v31-production-and-sale-priority) v1 | Ahmed Berat Özer | 2026-09-11 | 2575.6 (v1, 2026-09-09) | 2575.6 | yes | -7,728 / -8,842 (W 0/2) | 167 | new | Ozer V-series (v28/v25) on yhay81 shop-router-0908/0909 | crop public-order production, sale lead, terminal cargo rescue |
| 9 | A | [arsgorynich/kaggriculture-v43-local-confirmed](https://www.kaggle.com/code/arsgorynich/kaggriculture-v43-local-confirmed) v1 | Arsgorynich | 2026-09-15 | 2550.5 (v1, 2026-09-15) | 2550.5 | yes | -4,491 / -6,072 (W 0/2) | 170 | = pool/ozer_v43 (byte-identical) | exact Ozer V43 | sells stock only when dawn cargo would overflow the 100-slot shed |
| 10 | A | [ravi123a321at/177-180-fresh-top-30-v21-1-conditional-memory](https://www.kaggle.com/code/ravi123a321at/177-180-fresh-top-30-v21-1-conditional-memory) v1 | Ravindra | 2026-08-06 | 2517.1 (v1, 2026-08-06) | 2517.1 | yes | -56,700 / -42,687 (W 0/2) | 404 | new (Aug) | fit-only route tape + Top-30 route memory (Aug meta) | nearest public-route memory reorders existing SELLs; no geese/carrot/tomato |
| 11 | A | [aurax7/kaggriculture-shop-router-reactive-v7](https://www.kaggle.com/code/aurax7/kaggriculture-shop-router-reactive-v7) v1 | Yaxon | 2026-09-17 | 2689.9 (v1, 2026-09-17) | 2510.0 | yes | -3,778 / -5,528 (W 0/2) | 150 | new (pool has only yaxon reactive v5 copy) | Ozer V45 chassis + V44 race escalator + jaxa623 2842 advance/front-load overlay | horizon-24 reservations, 2-turn advance sales, market front-loading, low-spread attack |
| 12 | A | [nathanjacob/kaggriculture-pipe-5-terminal-boost](https://www.kaggle.com/code/nathanjacob/kaggriculture-pipe-5-terminal-boost) v7 | Nathan Jacob | 2026-09-15 | 2500.5 (v7, 2026-09-15) | 2500.5 | yes | -4,514 / -6,076 (W 0/2) | 184 | new | Ozer EXP260 (V41-V43) chassis | V43-like + terminal-day sale boost |
| 13 | A | [reyhanksatria/best-market-agent-high-strategy](https://www.kaggle.com/code/reyhanksatria/best-market-agent-high-strategy) v1 | Reyhan Ksatria | 2026-08-14 | 2517.5 (v1, 2026-08-14) | 2497.9 | yes | -54,665 / -43,751 (W 0/2) | 95 | new (Aug) | boatlee 10C4S (BL-MDgogo) route reconstructed from 12 public traces | 10 cows / 4 sheep consensus route tape + generic guards |
| 14 | A | [degnonguidi/kaggriculture-cloning-agent](https://www.kaggle.com/code/degnonguidi/kaggriculture-cloning-agent) v4 | renji_starfall | 2026-09-15 | 2735.1 (v4, 2026-09-15) | 2493.2 | yes | -3,979 / -6,139 (W 0/2) | 223 | = pool/ozer_v45 (byte-identical) | exact Ozer V45 | V44 + turn-0 single-order 70-wheat buy/sell round trip |
| 15 | A | [web3cainiao/kaggriculture-v21-tactical-memory](https://www.kaggle.com/code/web3cainiao/kaggriculture-v21-tactical-memory) v1 | webcainiao | 2026-08-06 | 2491.7 (v1, 2026-08-06) | 2491.7 | yes | -59,773 / -38,457 (W 0/2) | 101 | new (Aug) | fit-only route medoid + Top-30 market memory (Aug meta) | 8 cows/6 sheep, strawberry+melon; no geese |
| 16 | B | [guruprasaathas111/kaggriculture-top-2-master-engine-v4](https://www.kaggle.com/code/guruprasaathas111/kaggriculture-top-2-master-engine-v4) v4 | Guru Prasaath S | 2026-09-27 | 2784.6 (v4, 2026-09-20) | 2035.5 | yes | -1,769 / -1,300 (W 0/2) | 294 | = pool/tschinkel_metav4_v13 (byte-identical; new0926 copy is the later v11) | tschinkel Metav4 v13 = public V39 + v9 layers RACEPX/RACE/COURIER/CARROT/HERD | Metav4: race reservation from step 192 (horizon 40/margin 12), courier, extra carrot + herd layer |
| 17 | B | [flexonafft/kaggriculture-multi-route-farming-agent](https://www.kaggle.com/code/flexonafft/kaggriculture-multi-route-farming-agent) v59 | Igor Zharov | 2026-09-28 | 2767.3 (v59, 2026-08-14) | 1664.6 | yes | -33,151 / -30,560 (W 0/2) | 30 | new (nb copy is an older version) | prvsiyan 'soil' modal route + boatlee RC5 weed repair (embedded exec'd parents) | open-loop modal route, only weed repair; no geese, 56 wheat tiles, land on d6+d10 |
| 18 | B | [guruprasaathas111/kaggriculture-master-engine-v3](https://www.kaggle.com/code/guruprasaathas111/kaggriculture-master-engine-v3) v3 | Guru Prasaath S | 2026-09-25 | 2712.8 (v3, 2026-09-09) | None | yes | -3,957 / -9,185 (W 0/2) | 94 | new (new0926 copy is v25) | tiny tape replayer; same 5 MB actions.json as Gluzdov Seven-Turn Rescue | replays public tape for the shop pair + weed repair + 1 advanced sale |
| 19 | B | [haodou092/kaggriculture-harvest-ledger](https://www.kaggle.com/code/haodou092/kaggriculture-harvest-ledger) v54 | haodou092 | 2026-09-28 | 2684.2 (v54, 2026-09-20) | 2034.4 | yes | -1,719 / -1,346 (W 0/2) | 395 | new | Pipe-16 HybridOpening (nathanjacob) + Metav4 (tschinkel) V54 | idle workers grow one temporary wheat crop on days 0-2, then restore pasture |
| 20 | B | [degnonguidi/kaggriculture-utils-v1](https://www.kaggle.com/code/degnonguidi/kaggriculture-utils-v1) v8 | renji_starfall | 2026-09-24 | 2633.2 (v8, 2026-09-15) | 1415.8 | yes | -4,491 / -6,072 (W 0/2) [=same main.py as arsgorynich] | 170 | = pool/ozer_v43 (byte-identical) | exact Ozer V43 | as Ozer V43 |
| 21 | B | [leoprovorov/god-s-mode-hacked-stores](https://www.kaggle.com/code/leoprovorov/god-s-mode-hacked-stores) v7 | AlekseiProvorov | 2026-09-28 | 2604.3 (v7, 2026-09-19) | 2147.2 | yes | -3,545 / -1,795 (W 0/2) | 281 | = new0926/god-s-mode-hacked-stores | Metav4 v9/3 base_agent + shop_predictor + shop_overlay (4 files) | predicts which shops unlock and overlays shop-demand-aware sales |
| 22 | B | [tetsutani/demand-preserving-turn-sale-timing](https://www.kaggle.com/code/tetsutani/demand-preserving-turn-sale-timing) v1 | tetsu2131 | 2026-09-28 | 2604.0 (v1, 2026-09-18) | 2226.4 | yes | -3,257 / -5,807 (W 0/2) | 160 | new (new0926 copy is later v15) | Ozer V43/V48 chassis + ADV/RACE | moves ready cash-product sales 3 ticks earlier; lock-step order-book permutation |
| 23 | B | [guruprasaathas111/kaggriculture-master-engine-v53e01d74d8f](https://www.kaggle.com/code/guruprasaathas111/kaggriculture-master-engine-v53e01d74d8f) v2 | Guru Prasaath S | 2026-09-28 | 2581.0 (v2, 2026-09-13) | 1278.4 | yes | -3,789 / -6,585 (W 0/2) [=same main.py as ahmedberatozer] | 136 | = Ozer V39 (byte-identical) | exact Ozer V39 | as Ozer V39 |
| 24 | B | [anhadmahajan06/kaggriculture-autonomous-ai-farming-agent](https://www.kaggle.com/code/anhadmahajan06/kaggriculture-autonomous-ai-farming-agent) v5 | Anhad Mahajan | 2026-09-24 | 2578.7 (v5, 2026-09-20) | 1621.8 | yes | -1,769 / -1,300 (W 0/2) [=same main.py as guruprasaathas111] | 294 | = pool/tschinkel_metav4_v13 | exact tschinkel Metav4 v13 | as Metav4 v13 |
| 25 | B | [leoprovorov/31415926535897932384626433832795058202884197169399](https://www.kaggle.com/code/leoprovorov/31415926535897932384626433832795058202884197169399) v3 | AlekseiProvorov | 2026-09-27 | 2552.1 (v3, 2026-09-20) | 1645.5 | yes | -3,851 / -2,214 (W 0/2) | 292 | new | Gluzdov 'A Smaller Market Shock' on 2945 Farm / Metav4 v9/3 | idle opening worker grows one extra wheat crop before tile becomes pasture |
| 26 | B | [lynnsakurai/farmer-john-and-the-idle-seller](https://www.kaggle.com/code/lynnsakurai/farmer-john-and-the-idle-seller) v1 | Arlene | 2026-09-27 | 2542.6 (v1, 2026-09-20) | 2167.5 | yes | -1,719 / -1,346 (W 0/2) | 334 | new | harvest-ledger V54 (Pipe-16 + Metav4) | V54 + conservative idle-opening/market-queue closure (same results as harvest-ledger in smoke) |
| 27 | B | [leoprovorov/a-song-of-ice-and-fire-fixed-flexible](https://www.kaggle.com/code/leoprovorov/a-song-of-ice-and-fire-fixed-flexible) v6 | AlekseiProvorov | 2026-09-28 | 2513.1 (v6, 2026-09-20) | 2343.0 | yes | -1,769 / -1,300 (W 0/2) [=same main.py as guruprasaathas111] | 294 | = pool/tschinkel_metav4_v13 (best v6; new0926 copy is later v23) | exact tschinkel Metav4 v13 | as Metav4 v13 |
| 28 | B | [nihilisticneuralnet/kaggriculture-population-robust-economy](https://www.kaggle.com/code/nihilisticneuralnet/kaggriculture-population-robust-economy) v4 | parthenos | 2026-09-24 | 2502.0 (v4, 2026-09-21) | 1709.6 | yes | -2,255 / -1,151 (W 0/2) | 325 | new (nb copy is older) | Pipe-16/Metav4 V56 -> V57 | clone-aware premium-sale reservation horizon 41->48 turns |
| 29 | C | [raykkretzschmar/kaggriculture-rank-your-agent](https://www.kaggle.com/code/raykkretzschmar/kaggriculture-rank-your-agent) v11 | Rayk Kretzschmar | 2026-09-13 | 2990.4 (v11, 2026-08-09) | None | yes | -36,311 / -32,661 (W 0/2) | 14 | new | distilled trajectory of THUNDER THUNDER ep 91364946 + c17/c27 controller | open-loop replay of one top episode; ladder-ranking notebook |
| 30 | C | [ahmedberatozer/kaggriculture-v44-winning-the-same-turn-sale-race](https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v44-winning-the-same-turn-sale-race) v1 | Ahmed Berat Özer | 2026-09-15 | 2799.6 (v1, 2026-09-15) | None | yes | -3,950 / -6,110 (W 0/2) | 195 | new | Ozer V43 + clone-gated sale pre-emption | when rival executes same tape, advance same-turn sales to win pre-glut quote |
| 31 | C | [ahmedberatozer/kaggriculture-v48-clear-the-queue](https://www.kaggle.com/code/ahmedberatozer/kaggriculture-v48-clear-the-queue) v1 | Ahmed Berat Özer | 2026-09-17 | 2752.4 (v1, 2026-09-17) | None | yes | -3,973 / -5,469 (W 0/2) | 179 | new | Ozer V47 | drop empty sale slots, merge repeated cash sales, pull executable sales into freed slots |
| 32 | C | [jaxa623/2780-beyond-48-0-128-128-worlds-with-95-cis](https://www.kaggle.com/code/jaxa623/2780-beyond-48-0-128-128-worlds-with-95-cis) v1 | sdy623 | 2026-09-17 | 2780.9 (v1, 2026-09-16) | None | yes | -3,800 / -5,550 (W 0/2) | 204 | new | embedded exact Ozer V43 + jaxa623 K0006 wrappers | step-0 wheat round trip, horizon 24, market front-loading, 2-turn advance of cash products |
| 33 | C | [jaxa623/2802-two-identical-agents-90-points-apart](https://www.kaggle.com/code/jaxa623/2802-two-identical-agents-90-points-apart) v1 | sdy623 | 2026-09-17 | 2775.3 (v1, 2026-09-16) | None | yes | -3,778 / -5,528 (W 0/2) | 140 | new | Ozer V43 + K0009 open10 wrappers | as K0006 with 10-order opening |
| 34 | C | [lynnsakurai/farming-score-v2-a-better-approach](https://www.kaggle.com/code/lynnsakurai/farming-score-v2-a-better-approach) v2 | Arlene | 2026-09-19 | 2766.3 (v2, 2026-08-13) | 1584.5 | yes | -33,792 / -29,699 (W 0/2) | 13 | new | lean premium-lead controller (boatlee 8C4S-style) | 8 cows + 4 sheep backbone, weed repair, 1-turn premium sale lead, terminal liquidation |
| 35 | C | [guruprasaathas111/game-theoretic-master-discrete-optimization](https://www.kaggle.com/code/guruprasaathas111/game-theoretic-master-discrete-optimization) v2 | Guru Prasaath S | 2026-09-19 | 2745.0 (v2, 2026-09-19) | 2468.7 | yes | -3,417 / -2,355 (W 0/2) | 197 | new | Ozer EXP260 chassis + _V92 table (uncompressed) | Ozer V43-family with Metav4 _V92 table |
| 36 | C | [prvsiyan/kaggriculture-frontier-the-moon-counts-melons](https://www.kaggle.com/code/prvsiyan/kaggriculture-frontier-the-moon-counts-melons) v11 | prvsiyan | 2026-09-22 | 2736.1 (v11, 2026-08-04) | 2473.2 | yes | -71,541 / -42,407 (W 0/2) | 173 | new (pool has prvsiyan_soil) | fixed replay of Subin An ep 89945750 seat 1 (best v11, Aug-Sep) | open-loop recorded action trace, no geese |

**Legend:**
- **margin** = candidate − v5_market final bank in that game.
- **known?** compares main.py bytes against `adil-board/opponents/{pool,nb,new0926}`. The `new0926` copies are the kernels' *current* versions, not their best versions.

## Behaviour profile (seat 0 vs v5_market; mean of seeds 11 and 12; from tiles/orders)

| agent | final $ | geese/cows/sheep (max on tiles) | 2 geese by day | land bought on day | HIRE orders | hands mid-day avg/max | wheat bought | money gap vs v5 at end of d11 / d16 / d21 / d29 |
|---|---|---|---|---|---|---|---|---|
| **v5_market (ours, opponent)** | 93,755 | 3.7 / 7.3 / 6.1 | 7 or 11 | 6, 11 (+18 in ~40%) | 272 | 9.1 / 12.6 | 125 | — |
| haodou092 harvest-ledger V54 | 86,071 | 4 / 7 / 6 | 9 | 6, 11 (+18 in 1 of 2) | 276 | 9.2 / 13 | 138 | −74 / −106 / −956 / −1,192 |
| top-2-master-engine-v4 (= Metav4 v13) | 86,049 | 4 / 7 / 6 | 9 | 6, 11 (+18 in 1 of 2) | 276 | 9.2 / 12.5 | 138 | −124 / −156 / −1,006 / −1,194 |
| nihilistic V57 | 86,030 | 4 / 7 / 6 | 9 | 6, 11 (+18 in 1 of 2) | 276 | 9.2 / 13 | 135 | −14 / −46 / −848 / −1,308 |
| Ozer V55 | 85,787 | 4 / 7 / 6 | 9 | 6, 11 (+18 in 1 of 2) | 276 | 9.2 / 13 | 135 | −14 / −46 / −896 / −1,421 |
| god-s-mode | 85,612 | 4 / 7 / 6 | 9 | 6, 11 (+18 in 1 of 2) | 278 | 9.2 / 12.5 | 138 | −127 / −347 / −1,252 / −2,325 |
| aurax7 reactive v7 | 82,952 | 3 / 8 / 6 | 11 | 6, 11 (+18 in 1 of 2) | 278 | 9.2 / 12.5 | 127 | −362 / −346 / −1,902 / −3,938 |
| tetsutani demand-preserving v1 | 82,858 | 3 / 8 / 6 | 11 | 6, 11 (+18 in 1 of 2) | 278 | 9.2 / 12.5 | 149 | −338 / −218 / −1,878 / −3,831 |
| Ozer V48 | 82,692 | 3 / 8 / 6 | 11 | 6, 11 (+18 in 1 of 2) | 278 | 9.2 / 12.5 | 149 | −342 / −218 / −1,920 / −4,021 |
| Ozer V39 | 82,401 | 3 / 8 / 6 | 11 | 6, 11 (+18 in 1 of 2) | 275 | 9.2 / 12.5 | 159 | −1,120 / −712 / −2,988 / −4,530 |
| master-engine-v3 (tape replayer) | 72,015 | 3 / 8 / 6 | 11 | 6, 11 | 260 | 8.7 / 11 | 155 | −1,668 / −1,346 / −2,302 / −5,592 |
| flexonafft multi-route v59 | 82,412 | **0** / 7.5 / 4 | — | 6, 10 | 264 | 8.7 / 14 | 189 | −11,988 / −17,980 / −21,792 / −31,322 |
| prvsiyan moon-counts-melons v11 | 68,797 | **0** / 8 / 6 | — | 7, 10 | 306 | 10.1 / 12 | **967** | −16,842 / −22,670 / −29,082 / −51,634 |
| web3cainiao v21 | 62,332 | **0** / 8 / 6 | — | 7, 10 | 275 | 9.0 / 14 | 275 | −12,886 / −17,018 / −26,255 / −47,109 |

Max planted tiles per crop:
- Horizon family: wheat 38, carrot 29–33, strawberry 32–33, melon 12, tomato 0 or 10 depending on the world.
- flexonafft: wheat 56, strawberry 35, melon 12, no carrot or tomato.
- moon: strawberry 40, wheat 32, melon 11.
- v21: strawberry 39, wheat 31, melon 13.

I do not report SELL unit counts. They come from submitted orders, and several agents submit oversized sweep orders, so the counts overstate what actually sold.

## Observations
1. **Public notebook scores do not show code strength.**
   - The current search score tops out at 2625 (Ozer V38). The LB top was about 3063 on 2026-09-23.
   - Best-version scores above 2700 come from versions that ran earlier: August, or Sept 9–20.
   - Re-running the same code later scores much lower. Examples:
     - Metav4 v13, published as top-2-master-engine-v4: v4 2784.6, current v11 2035.5.
     - flexonafft: v59 2767.3 (Aug 14), current v103 787.7.
     - master-engine-v3: v3 2712.8, current v25 2041.0.
   - Treat these numbers as ladder timing, not strength.
2. **Almost everything public now is one code family.**
   - 26 of the 32 unique agents carry the Horizon / Ozer shop-router tape chassis. The markers are `DEFAULT_SETTINGS`, `make_agent`, `_R37_HORIZONS` and the embedded `actions.json` tapes.
   - Upstream chain: thomastschinkel runtime → yhay81 shop-router-0908/0909 tapes and 13 shop-pair routes → Ozer V25…V57. prvsiyan, aurax7, Dmitrii Gluzdov, Rayk Kretzschmar and jaxa623 contributed layers along the way.
   - Many "new" notebooks are byte-identical reposts:
     - Metav4 v13 appears 3 times: top-2-master-engine-v4, autonomous-ai-farming-agent, a-song-of-ice-and-fire v6.
     - Ozer V43 appears twice: arsgorynich v43-local-confirmed, degnonguidi utils-v1.
     - Ozer V45 is reposted as degnonguidi cloning-agent.
     - Ozer V39 is reposted as master-engine-v53e01d74d8f.
3. **None of the public agents beats our v5_market locally (0/64 games).**
   - The closest are the Pipe-16 HybridOpening + Metav4 line: harvest-ledger V54 and farmer-john-idle-seller (−1.7k / −1.3k), Metav4 v13 (−1.8k / −1.3k), nihilistic V57 (−2.3k / −1.2k), Ozer V53 (−1.3k / −1.5k) and Ozer V55 (−2.0k / −1.5k).
   - The Ozer V31–V48 chassis variants (incl. jaxa623, aurax7, tetsutani, pipe-5, game-theoretic) trail by 2.4–9.6k per game.
   - August route-memory tapes and open-loop episode traces trail by 29–72k: v21, v21.1, BL-MDgogo, flexonafft, lynnsakurai lean, Rayk THUNDER trace, prvsiyan moon.
4. **Herd sizes:**
   - The Horizon family holds 3–4 geese, 7–8 cows and 6 sheep. The Metav4 / Pipe-16 line has 2 geese by day 9 and 4 geese in total. Ozer V39/V48, tetsutani and aurax7 reach 2 geese only by day 11 and keep 3.
   - The independent lines (flexonafft, moon, v21, lean 8C4S) keep **no geese** at all.
   - No public agent runs the ~6-geese-by-day-11 programme that `adil-board/research/gap_vs_top.md` measured for top-20 ladder teams.
5. **Land and hires are identical across the family, so they don't separate these agents.**
   - Quadrant 2 is bought on day 6 and quadrant 3 on day 11. A 4th quadrant (day 18) is bought in only one of the two worlds.
   - About 275 HIRE orders per game, about 9 hands mid-day, 12–13 at peak.
   - The independents buy land on day 6/7 + 10 and never a 4th quadrant.
6. **Where the money gap opens:** the family runs almost identically to v5_market through day 16 (gap under ~$350, except Ozer V39 at about −$1.1k and the tape replayer master-engine-v3 at −$1.7k on day 11). The deficit builds on days 17–29. The differentiators are therefore late-game market mechanics:
   - premium-sale reservation horizon: Metav4 RACE from step 192 with horizon 40, V55 uses 41, V57 uses 48;
   - same-turn sale races against clones (V44 race, jaxa623 front-loading and 2-turn advance, tetsutani 3-tick ADV);
   - queue cleanup (V48).
   Production is not the differentiator.
7. **Opening-market micro-tricks:** every family agent sells from turn 0.
   - Ozer V45 does a 70-wheat buy-and-sell round trip in one order.
   - jaxa623 K0006 does a single-order step-0 round trip.
   - Ozer V53 detects the rival's opening from its step-2 wheat inventory.
   - Wheat bought as feed is 125–160 units per game (v5 ~125). moon buys about 970 because it has no wheat plan.
8. **Newest public ideas (Sept 20–28) are small labour tweaks:**
   - "Productive idle workers": in the Pipe-16 line (V54 harvest-ledger, V55) and Gluzdov's "A Smaller Market Shock" (leoprovorov 3141…), idle hands grow one temporary wheat crop on days 0–2 before the tile becomes pasture. The day-6 bank differs from v5_market by only −$8…+$52 for these agents.
   - Shop-unlock prediction overlay: god-s-mode.
   - Neither changes the mid-game economy.
9. **Shop routing** in every family agent is a lookup keyed by the unlocked shop pair: `_R108_SHOP_ROUTES`, or the 15-entry `SHOP_PLANS` table in master-engine-v3. The same 5 MB `actions.json` tape bank is shared by master-engine-v3 and kaggricult-man.
10. **Runtime:** the worst per-turn time is 639 ms (Ozer V53, which runs an opponent-sale forecaster). The Metav4-family agents run at 200–400 ms, and the small tape agents at 11–100 ms. None timed out.
