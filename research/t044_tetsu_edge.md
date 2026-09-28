# T044 — public tetsutani Step1009 market edge

Local official-engine only; no Kaggle access or submission. Raw replay JSON was deleted after parsing. Aggregate audit: `research/t044_tetsu_edge_stats.json`; hook miner: `wt/codex/lab/t044/analyze.py`.

## Experiment

| matchup | fresh worlds | games | result from tetsu perspective |
|---|---:|---:|---:|
| `tetsu_base` vs `tetsu_wm` | 16 × both seats | 32 | −$24.88/world; paired bootstrap 95% [−$47.75, −$6.81] |
| `tetsu_base` vs byte-identical `tetsu_base` | 16 × both seats | 32 | exactly $0.00/world (16 draws) |

Seeds were 184431–34, 184451–62 (wm), and 184441–44, 184471–82 (mirror). Four initial non-counting games aborted on OpenBLAS thread creation while Claude's RR was live; every counted game is DONE/DONE with BLAS pinned to one thread. This does **not** reproduce the reported $350–1000 tetsu advantage: on independent worlds `wm` has a small +$24.88 edge. The two large single-seat deviations ($12,839 and $2,989) cancel exactly when both seats are averaged.

## Final-money decomposition (mean dollars/game)

`wm − tetsu` is inventory/market only, not a different farm plan.

| flow | tetsu | wm | wm − tetsu |
|---|---:|---:|---:|
| final money | 109,187.69 | 109,212.56 | **+24.88** |
| WHEAT product buys | −4,809.59 | −4,998.72 | −189.13 |
| WHEAT sales | 12,866.88 | 13,070.63 | +203.75 |
| EGG sales | 2,779.25 | 2,792.56 | +13.31 |
| FERTILIZER sales | 14,727.00 | 14,723.94 | −3.06 |
| cows/sheep/goose buys | −7,509.38 | −7,509.38 | 0.00 |
| land / hires | −3,500.00 / −4,993.12 | same | 0.00 |
| all other seed/product flows | same | same | 0.00 |

Accounting reconciles exactly in every replay: `initial $3,000 + successful SELL − successful market BUY − land − hire = final money`. A tetsu mirror's gross sale mix is STRAWBERRY $26,797, MILK $21,085, WHEAT $20,536, WOOL $16,407, FERTILIZER $14,760, MELON $14,267, CARROT $7,896, EGG $4,258, TOMATO $2,826. This describes scale, not marginal value.

## Actual market delta

The only source difference is T031's append-only WHEAT block. It appends one order only if the parent has no WHEAT order and a slot is free. Published parameters: BUY d6–17, observed quote ≤30, shed WHEAT<20, cap8, cash reserve $2,000; else SELL d10–28, observed quote≥40, held>35, cap8, retain35.

Realised `wm − tetsu` WHEAT cash deltas (including subsequent tape response, so not a causal attribution of each appended order) are d10 +$97.19, d11 +$112.62, d12 −$137.38, d13 −$69.50, d17–22 net +$93.38, d23–28 net −$81.69. The whole WHEAT season is only +$14.62; incidental EGG/FERTILIZER movement adds +$10.25. A pre-turn ≤30 quote can become a d10 BUY fill around $37–39 after same-turn demand, so it is not a safe cheap-fill guarantee.

## Contested mirror goods

Across 32 mirror games, successful same-day two-sided sales: FERTILIZER 920, WHEAT 824, MILK 672, WOOL 588, STRAWBERRY 440, EGG 372, CARROT 156, MELON 64, TOMATO 24. Prices match to displayed precision for every good (WHEAT mean absolute gap $0.00055; all others $0). Thus no execution-priority leak exists in an exact mirror; same policy draws. FERTILIZER is highly contested but already follows a declining-price sell/buy sequence (d1 sales $99.7 → d27 buys $8.2), not usable round-trip arbitrage.

## Ranked append-only screen rules — not claimed improvements

All retain fail-open conditions: `step<718`, free market slot, deep-copy `market` only, no unit action change, and skip when the parent already orders that good. These are screen candidates, never ladder candidates without an independent both-seat whole-world gate.

1. **Existing bounded WHEAT layer (control):** exact parameters above. The sole evidence-backed overlay, but only +$24.88/world here; it cannot explain a $350+ clone gap.
2. **Safer WHEAT feed probe:** `BUY_PRODUCT WHEAT q≤4`, d6–9, observed quote≤25, held<16, cash after order≥$2,400, no parent WHEAT order. It tests a truly cheap reserve while avoiding the d10–13 self-price impact; correct outcome may be inert.
3. **CARROT peak-window sale:** `SELL CARROT q≤8`, d25–27, quote≥65, shed≥16, retain8, no parent CARROT order. Mirror price peaks near $67/$71/$69 on d25–27 before the d29 $49 terminal clear. Activation is uncertain because the tape normally sells it.
4. **STRAWBERRY pre-glut sale:** `SELL STRAWBERRY q≤6`, d20–21, quote≥110, shed≥12, retain6, no parent STRAWBERRY order. Mirror quote falls $133 → $107 → $70 on d20–22; this only rescues a missed sale turn.
5. **Negative rule — no FERTILIZER append-only round trip:** frequent contention is not a signal; there is no later high-price exit, and prior T031 evidence rejects it.

Structural conclusion: an append-only layer cannot defer tetsu's already-contested WHEAT/FERTILIZER/MILK/WOOL/STRAWBERRY sales. It cannot systematically beat an exact mirror through sale timing alone; that needs a non-identical production/market policy and a fresh whole-world gate.
