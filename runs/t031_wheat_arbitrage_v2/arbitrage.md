# T031 — WHEAT buy/sell time audit

Exact 39 loss replays, official engine 1.32.7. `temporal_match` is FIFO cash-flow matching of a purchase to a later sale, not physical provenance: WHEAT is fungible and farms harvest it too. `shadow_extra` holds opponent purchases in shared inventory only; it is a local price-exposure accounting diagnostic, not a feasible behaviour counterfactual.

| per loss mean | value |
|---|---:|
| opp_buy_units | 1,074.69 |
| opp_buy_cost | 43,107.15 |
| opp_sell_units | 1,278.95 |
| opp_sell_revenue | 51,303.51 |
| cashflow_wheat | 8,196.36 |
| buy_mean_price | 36.94 |
| sell_mean_price | 38.58 |
| buy_mean_day | 12.81 |
| sell_mean_day | 20.32 |
| temporal_match_units | 1,073.18 |
| temporal_match_pnl | 571.79 |
| temporal_match_mean_hold_steps | 76.71 |
| town_price_delta_after_buy_mean | 0.56 |
| our_buy_units | 546.03 |
| our_buy_cost | 22,447.10 |
| our_buy_mean_price | 36.67 |
| our_shadow_extra_cost | 7,961.77 |

## Per opponent identity

| opponent | games | opp buy $ | opp sale $ | cash-flow $ | FIFO later-sale P&L $ | buy d | sell d | our shadow cost $ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Akhil Chinta | 1 | 310,522 | 318,308 | 7,786 | 1,125 | 19.5 | 19.7 | 730.0 |
| Bigplanedoesnotflyfast | 1 | 5,572 | 14,924 | 9,352 | 385 | 6.1 | 19.8 | 714.0 |
| Bohann Wang | 1 | 4,672 | 11,803 | 7,131 | 337 | 7.3 | 19.5 | 507.0 |
| Breaking1800 | 1 | 16,153 | 30,123 | 13,970 | 657 | 21.5 | 24.3 | 794.0 |
| Clement Lau | 1 | 4,209 | 14,125 | 9,916 | 278 | 8.2 | 20.4 | 417.0 |
| Farm Hullabaloo | 1 | 4,321 | 13,151 | 8,830 | 394 | 8.2 | 20.5 | 405.0 |
| FinalSunFlower | 1 | 69,140 | 75,972 | 6,832 | 189 | 14.6 | 16.3 | 32,205.0 |
| HD h Joratos | 1 | 4,280 | 13,498 | 9,218 | 339 | 7.9 | 21.6 | 398.0 |
| John Doge | 1 | 4,433 | 13,504 | 9,071 | 375 | 8.2 | 21.3 | 326.0 |
| Joseph Adamski | 1 | 77,693 | 87,126 | 9,433 | 356 | 12.5 | 13.7 | 1,743.0 |
| Mehrdad Naderi | 1 | 5,421 | 12,427 | 7,006 | 382 | 13.4 | 22.0 | 703.0 |
| Một hai ba bốn 5 sáu bảy tám 9 | 1 | 78,605 | 88,103 | 9,498 | 697 | 19.4 | 20.2 | 381.0 |
| Omar Althobaiti | 1 | 109,329 | 115,866 | 6,537 | 594 | 18.6 | 19.2 | 640.0 |
| QQ农场 | 1 | 141,315 | 150,841 | 9,526 | 3,428 | 18.2 | 18.8 | 75,503.0 |
| RYUSHI | 1 | 4,397 | 17,144 | 12,747 | 438 | 8.0 | 21.9 | 351.0 |
| Rio | 1 | 100,720 | 113,252 | 12,532 | 824 | 17.9 | 18.8 | 515.0 |
| Ryo | 1 | 4,792 | 10,012 | 5,220 | 384 | 8.7 | 19.8 | 491.0 |
| Shivcharanraju Anga | 1 | 4,551 | 13,547 | 8,996 | 356 | 8.2 | 20.4 | 338.0 |
| Silhouette | 1 | 5,987 | 11,599 | 5,612 | 392 | 13.5 | 22.0 | 802.0 |
| Takahiro Katsumata (tkatsuma) | 1 | 84,507 | 93,504 | 8,997 | 669 | 17.8 | 18.9 | 2,231.0 |
| Vasilii Buzmakov | 1 | 9,576 | 15,855 | 6,279 | 541 | 16.3 | 23.4 | 1,331.0 |
| We wanna be tomatos | 1 | 5,621 | 12,164 | 6,543 | 273 | 15.0 | 17.1 | 371.0 |
| Yakouu | 1 | 205,700 | 214,319 | 8,619 | 972 | 19.9 | 20.2 | 617.0 |
| Ziad EL ARARI | 1 | 4,668 | 10,773 | 6,105 | 256 | 7.3 | 19.9 | 619.0 |
| automatylicza | 1 | 4,117 | 12,756 | 8,639 | 335 | 7.9 | 21.4 | 506.0 |
| azamat1ch | 1 | 5,759 | 11,631 | 5,872 | 450 | 13.9 | 22.5 | 640.0 |
| base_camp_2002 | 1 | 5,761 | 8,991 | 3,230 | 461 | 14.1 | 22.1 | 683.0 |
| emreaydin | 1 | 193,749 | 203,670 | 9,921 | 812 | 16.8 | 17.4 | 79,642.0 |
| fuxi | 2 | 4,898 | 8,233 | 3,335 | 382 | 10.8 | 14.4 | 3,738.0 |
| hirayuki | 1 | 7,026 | 18,237 | 11,211 | 614 | 14.4 | 23.2 | 570.0 |
| istinetz | 1 | 7,647 | 15,119 | 7,472 | 578 | 12.3 | 23.1 | 328.0 |
| just_calculate | 1 | 4,321 | 9,762 | 5,441 | 295 | 8.2 | 20.2 | 405.0 |
| xi luo | 1 | 7,697 | 12,663 | 4,966 | 581 | 14.2 | 23.3 | 1,089.0 |
| yiyu0716 | 1 | 5,384 | 13,536 | 8,152 | 467 | 13.3 | 23.6 | 613.0 |
| Варим сельский самогон | 1 | 5,244 | 15,460 | 10,216 | 688 | 8.3 | 22.1 | 13,869.0 |
| もたざる | 1 | 5,390 | 14,510 | 9,120 | 480 | 13.3 | 23.6 | 602.0 |
| 我小栗帽要娶藤正进行曲！！！💍 | 1 | 3,097 | 13,809 | 10,712 | 318 | 7.1 | 23.0 | 488.0 |
| 일필휘지 | 1 | 150,007 | 162,287 | 12,280 | 816 | 17.9 | 18.6 | 80,466.0 |

Raw per-game values are in the adjacent JSON.
