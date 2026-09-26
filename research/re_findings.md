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
