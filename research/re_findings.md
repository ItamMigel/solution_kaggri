# Reverse-engineering findings (Claude, 2026-09-26 ~19:30Z) — exact replays (lab/re/trades.py, declog.py; research/re/*)
## Net $/game by source (executed trades)
| | DSM (48g, 98% W) | MMPQ (100g, 80%) | fuxi (40g) | Boey (100g, 39%) | ours es6/es7 (65g) |
|---|---|---|---|---|---|
| final money | 115.1k | 109.6k | 109.7k | 87.0k | 104.4k |
| EGG | **11.8k** | **11.1k** | 5.9k | 5.4k | **3.2k** |
| WHEAT sell − buy | 16.9−4.2 | 17.3−4.1 | 12.5−5.0 | 64.9−59.3 (churn) | 22.9−**14.0** |
| CARROT | 10.5k | 6.9k | 5.4k | 5.1k | 7.0k |
| MILK | 19.1k | 20.1k | 26.1k | 19.7k | 25.0k |
| goose buys | −2.2k | −2.1k | −1.0k | −1.1k | −0.6k |
## Daily plan (hour 2 snapshot, mean over games)
DSM ≈ MMPQ (same lineage, nearly identical numbers): d2 cow2 sheep3 wheat~11 melon~8; d8 2nd land + geese 2.7; **d10 3rd land, 7 geese (2 coops),
wheat ~20 tiles**, strawberry 21–24; later cows 7–7.7, sheep 5–7, wheat 20–35, carrots late (13–19 by d24–27).
Ours: 3rd land d12, geese 2 (from d12), wheat ~5 at d10 (feed BOUGHT: −14k), strawberry 33 (over-invested).
fuxi: 4th land (3.8 quads), tomatoes 13–17 tiles d18–24, geese 3.2.
Boey: wheat/fertilizer churn (buy+sell same turns, zero-cost round trips by the price formula), early melon 11 d3.
## Mechanism (hypothesis)
DSM/MMPQ system = early land (d8/d10) → big own wheat field feeding 7 geese + herd → eggs +8k and feed savings ~10k vs us;
fewer strawberries. Our G1 goose module added geese alone (no own feed, no early land) → failed. Need the whole system.
## Exact event timing (median over games; declog market orders)
| event | DSM | MMPQ | ours es6/es7 |
|---|---|---|---|
| 2nd quadrant order | d6.1 (step 147) | d6.1 | d6.2 (150) |
| **3rd quadrant order** | **d8.2 (196)** | **d8.2 (198)** | **d11.0 (265)** |
| **first goose order** | **d6.4 (153)** | **d6.4** | **d10.0 (241), only 38/65 games** |
| first melon sale | d10.2 | d10.2 | d10.4 |
Identical up to d6; they then buy land#3 2.8 days earlier and start geese 3.6 days earlier, BEFORE melon income (cash ~1.6k at d8),
while we spend on strawberries (33 vs 21–24 tiles) and early cows. => port their d6–d10 priorities, not their whole agent.
Decision-tree rules (lab/re/rules.py → research/re/rules_dsm_mmpq.md): land purchase keyed on shed MELON>17 / clock proxies — trees mostly learn the clock.
Openings: DSM/MMPQ diverge by step ~96 (reactive, no shared tape); Boey: 50% of games share an identical 199-step tape (one tape sub + one reactive).
