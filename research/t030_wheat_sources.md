# T030 — WHEAT source in es3 ladder losses

Official-engine re-execution of all 39 T028 losses and all 41 wins, with eight workers and successful-action instrumentation: [full daily report](../runs/t030_wheat_sources_v2/wheat.md), [JSON](../runs/t030_wheat_sources_v2/wheat.json).

In a loss the opponent sells 517 more WHEAT/game, but grows slightly less: −7.6 successful WHEAT plants and −8.0 harvested WHEAT units relative to us. Land is effectively equal after d11 (about 3.1--3.2 quadrants); opponent seasonal successful hires are only +4.0; FEED is only +5.0. The decisive observed flow is +528.7 `BUY_PRODUCT WHEAT` ($20.66k/game). This is consistent with purchased WHEAT market turnover/resale, not an own-feed advantage.

The tiny tape-safe repair was therefore deliberately conservative: default-off `PASS -> PLANT WHEAT` only at an actor's existing empty tile, consuming only an already spare WHEAT seed. Off identity is 0/1,442 action diffs. On fails a fresh two-world, both-seat es6+Parthenos screen 0/8 (paired −50pp, −$2,248; 16/16 valid), so it does not advance to T025 full panel.
