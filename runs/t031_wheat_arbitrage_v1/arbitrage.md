# T031 — WHEAT buy/sell time audit

Exact 39 loss replays, official engine 1.32.7. `temporal_match` is FIFO cash-flow matching of a purchase to a later sale, not physical provenance: WHEAT is fungible and farms harvest it too. `shadow_extra` holds opponent purchases in shared inventory only; it is a local price-exposure accounting diagnostic, not a feasible behaviour counterfactual.

| per loss mean | value |
|---|---:|
| opp_buy_units | 903.44 |
| opp_buy_cost | 36,884.13 |
| opp_sell_units | 1,107.54 |
| opp_sell_revenue | 45,027.54 |
| cashflow_wheat | 8,143.41 |
| buy_mean_price | 17.34 |
| sell_mean_price | 17.95 |
| buy_mean_day | 6.12 |
| sell_mean_day | 9.17 |
| temporal_match_units | 903.41 |
| temporal_match_pnl | 416.87 |
| temporal_match_mean_hold_steps | 27.22 |
| town_price_delta_after_buy_mean | 0.26 |
| our_buy_units | 717.28 |
| our_buy_cost | 28,670.13 |
| our_buy_mean_price | 19.92 |
| our_shadow_extra_cost | -2.95 |

## Per opponent identity

| opponent | games | opp buy $ | opp sale $ | cash-flow $ | FIFO later-sale P&L $ | buy d | sell d | our shadow cost $ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Akhil Chinta | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -4.0 |
| Bigplanedoesnotflyfast | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -4.0 |
| Bohann Wang | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -2.0 |
| Breaking1800 | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 |
| Clement Lau | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -5.0 |
| Farm Hullabaloo | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -5.0 |
| FinalSunFlower | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -19.0 |
| HD h Joratos | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -2.0 |
| John Doge | 1 | 8,831 | 27,276 | 18,445 | 768 | 8.1 | 21.4 | 0.0 |
| Joseph Adamski | 1 | 81,931 | 101,536 | 19,605 | 545 | 12.3 | 14.8 | 0.0 |
| Mehrdad Naderi | 1 | 10,983 | 24,490 | 13,507 | 761 | 13.7 | 22.0 | 0.0 |
| Một hai ba bốn 5 sáu bảy tám 9 | 1 | 83,026 | 103,572 | 20,546 | 1,151 | 18.7 | 20.5 | 0.0 |
| Omar Althobaiti | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -3.0 |
| QQ农场 | 1 | 284,630 | 301,752 | 17,122 | 1,372 | 18.2 | 18.9 | 0.0 |
| RYUSHI | 1 | 8,794 | 34,255 | 25,461 | 906 | 8.0 | 21.9 | 0.0 |
| Rio | 1 | 105,122 | 129,817 | 24,695 | 1,247 | 17.4 | 19.1 | 0.0 |
| Ryo | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -7.0 |
| Shivcharanraju Anga | 1 | 8,905 | 27,230 | 18,325 | 768 | 8.0 | 20.5 | 0.0 |
| Silhouette | 1 | 11,675 | 23,043 | 11,368 | 786 | 13.7 | 22.4 | 0.0 |
| Takahiro Katsumata (tkatsuma) | 1 | 89,841 | 107,558 | 17,717 | 1,018 | 17.6 | 19.5 | 0.0 |
| Vasilii Buzmakov | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -6.0 |
| We wanna be tomatos | 1 | 9,900 | 20,801 | 10,901 | 432 | 12.0 | 18.2 | 0.0 |
| Yakouu | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -7.0 |
| Ziad EL ARARI | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -7.0 |
| automatylicza | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -9.0 |
| azamat1ch | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -9.0 |
| base_camp_2002 | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -2.0 |
| emreaydin | 1 | 336,305 | 357,549 | 21,244 | 1,545 | 17.4 | 18.1 | 0.0 |
| fuxi | 2 | 35,852 | 47,304 | 11,451 | 516 | 12.8 | 17.8 | 0.0 |
| hirayuki | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -2.0 |
| istinetz | 1 | 12,050 | 31,494 | 19,444 | 1,010 | 10.6 | 22.6 | 0.0 |
| just_calculate | 1 | 8,526 | 19,903 | 11,377 | 626 | 8.1 | 20.2 | 0.0 |
| xi luo | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -2.0 |
| yiyu0716 | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -8.0 |
| Варим сельский самогон | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -4.0 |
| もたざる | 1 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | -8.0 |
| 我小栗帽要娶藤正进行曲！！！💍 | 1 | 8,574 | 28,955 | 20,381 | 678 | 11.0 | 23.3 | 0.0 |
| 일필휘지 | 1 | 297,683 | 322,236 | 24,553 | 1,612 | 18.1 | 18.9 | 0.0 |

Raw per-game values are in the adjacent JSON.
