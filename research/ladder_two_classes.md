# Ladder = two opponent classes (Claude, 2026-09-26 16:10Z) — from 80 es3_g5 ladder replays (replays/t028)
Class = share of turns d9–29 where opponent's hands+farmer positions equal ours (= Horizon RACE clone test).
| class | n | W-L | mean margin |
|---|---|---|---|
| tape-clone (same public route tape; ≥50% equal positions) | 70 | 40-30 | −170 |
| reactive / own route (<50%) | 10 | **1-9** | **−5,511** |
Reactive losses: fuxi −17.7k/−12.9k, Joseph Adamski −11.0k, istinetz −5.7k, Варим сельский самогон −2.6k, 我小栗帽… −2.4k.
Local pool: every strong public agent is a tape-clone (detector fires at step ~225: parthenos, metav4, yhay, t2945, ozer, yaxon, prvsiyan,
tetsu, 2965, shepherd, demand); the only non-clones (boatlee, fukami) are weak (we win by 30–40k). => all our gates measured the clone class only.
Implications: (1) near-mirror edges (es7_wm 30/32 vs es6; T033 knob switch) target 70/80 of ladder games; (2) the barrier to top (top-20 are reactive)
is the reactive class, which we cannot yet simulate locally.
