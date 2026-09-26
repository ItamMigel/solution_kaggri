# Production RE — top teams

Scope is planting/crop mix, unit production allocation, and herd/structures. Market, land and hiring belong to Claude's macro analysis. We never submit to Kaggle.

## Method

`lab/re/declog.py` gives a pre-action state and aggregate unit-operation counts, not target coordinates. Crop changes below use the next logged state. “Priority” therefore means observed scheduling/co-occurrence until raw actions are joined to target tiles.

Boey has 108 complete 719-turn trajectories. Development is trajectories 1–86 in log order; held-out is 87–108. The baseline predicts each operation's development-mode count at `(day,hour)`, and is evaluated on every teacher-forced held-out turn. It is a calendar baseline, not a claim that Boey ignores state.

## Boey (#1)

### Explicit crop/planting rule

| days | rule | median day-start state (S/C/M/T/W) |
|---|---|---|
| d0–2 | bootstrap **7 MELON + 12 WHEAT**; finish melon d1–2 | d1 0/0/7/0/12 |
| d3–6 | replace early wheat with STRAWBERRY; second strawberry fill d6 | d7 19/0/12/0/2 |
| d8–11 | continuously replant WHEAT, complete strawberry build | d11 26/0/6/0/22 |
| d12–22 | retain S while MELON exits; refill WHEAT; introduce small CARROT and occasional TOMATO | d16 22/2/2/0/15; d22 11/3/1/0/17 |
| d23–27 | terminal STRAWBERRY→CARROT rotation while WHEAT remains high | d25 4/8/0/0/24; d27 4/13/0/0/22 |
| d28–29 | no new planting | run down crops |

This is genuine replanting, not only initial sowing: all 86 development trajectories add STRAWBERRY on d6 (median +11 net tiles); all add WHEAT on d8, d10, d13–16, d18, d20 and d22–24. CARROT is late: adds on d19/d20/d23 in 73/86, 74/86 and 83/86 respectively. Shop history currently repeats names, so it is not yet a valid conditioning feature; do not encode shop-specific crop branches before normalising it.

### Herd, structures, fertilizer

* d1: 5 PASTURE, 3 COW, 2 SHEEP; d3: 5 PASTURE, 2 COOP, 2 GOOSE.
* d7: 11 PASTURE, 4 COW, 6 SHEEP, 2 GOOSE; d11: 13 PASTURE, 2 COOP, 4/7/2 herd.
* d12: 6 COW; d17: 10 SHEEP and 17 PASTURE; d24: 18 PASTURE, 2 COOP, 5 COW, 11 SHEEP, 2 GOOSE.

The production policy is thus animal-active from d0–3, later expands sheep/pasture, and holds geese near 2. Fertilized tiles have median zero through d11, then 3/4/9 on d12–14, 18 on d16 and about 12–20 thereafter: explicit current rule is **do not fertilize the bootstrap; begin after d11 and retain a nonzero fertilized crop base**. Target-tile choice remains unknown.

### Unit allocation and held-out agreement

At herd size 10+, mean units/turn are WATER 1.59, HARVEST .78, CARE .70, FEED .72, COLLECT_FERTILIZER .72 and FERTILIZE .32 (61,219 turns). With no animals all seven production operations are exactly zero (341 turns); at 1–9 animals, service counts are only about .22–.23. This supports scaling animal service with herd and WATER/HARVEST with the crop base. CARE+FEED occur together on only 35.6% of turns containing either; CARE+COLLECT on 26.9%, so a clone must route individual workers rather than bind a three-op triplet.

| operation | held-out presence | held-out exact count | MAE |
|---|---:|---:|---:|
| PLANT | 83.1% | 80.4% | .277 |
| WATER | 84.7% | 62.8% | .696 |
| HARVEST | 81.3% | 73.0% | .406 |
| CARE | 77.4% | 71.1% | .428 |
| FEED | 77.4% | 70.5% | .426 |
| FERTILIZE | 86.3% | 84.2% | .202 |
| COLLECT_FERTILIZER | 77.3% | 71.5% | .436 |

Calendar phase captures much of the aggregate decision but is not a playable clone: next step is raw target/path reconstruction and state-bucket residuals (ripe/water need, animal status, carried fertilizer).

## M&M&P&Q

134 full trajectories; development trajectories 1–107, held-out 108–134. M&M&P&Q shares the broad crop calendar with Boey but has a materially stronger early cow/goose build and earlier fertilizer.

| days | explicit crop rule | median day-start state (S/C/M/T/W) |
|---|---|---|
| d0–2 | bootstrap **6 MELON + 10 WHEAT**, finish MELON on d1 and small WHEAT refill d2 | d1 0/0/6/0/10; d2 0/0/10/0/10 |
| d3–6 | grow STRAWBERRY; complete a larger d6 strawberry+melon fill | d7 22/0/12/0/1 |
| d8–21 | replant WHEAT every day while holding STRAWBERRY 23–27; only sparse CARROT/TOMATO probes | d12 25/0/2/0/27; d19 26/0/0/0/20 |
| d22–27 | decisive STRAWBERRY→CARROT terminal rotation and WHEAT fill | d23 7/5/0/0/34; d27 3/17/0/0/30 |
| d28–29 | no material new plants | run down |

All 107 development trajectories add MELON/WHEAT at d0, STRAWBERRY at d6 (median event +16), and WHEAT at d8, d10, d13–16, d18, d20 and d22–24. The CARROT conversion begins a day earlier in the state (d22) and becomes near-universal: additions d23/d24/d25/d26 occur in 73/85/88/88 of 107 trajectories. This is a robust production rule rather than a one-shop exception.

Herd/structure rule: d1 starts 5 PASTURE, **2 COW/3 SHEEP**; by d5 it is 8 PASTURE and 5/3/0. It adds COOP/geese aggressively: d7 10 PASTURE/2 COOP and **6/3/2**, d8 10/3 and 7/3/3, d10 13/7 and **7 COW/3 SHEEP/7 GOOSE**. It holds 7 geese and 7 cows to d19, adds sheep to 5 from d16, and finishes around 6/5/7 with 11–14 pasture and 7 coop. This is the clearest production distinction from Boey's small, capped goose herd.

Fertilizer starts d11 (median 6 tiles) rather than Boey's d12, rises 8/10/14 on d12–14 and reaches 28–31 d16–20: rule `after d10, fertilize most of the standing crop base`, then retain about 21–30 fertile tiles through d29.

For herd≥10, mean units/turn are WATER 1.80, HARVEST .89, CARE .62, FEED .62, FERTILIZE .39, COLLECT_FERTILIZER .76 (75,654 turns); at herd 1–9 they are .57/.12/.28/.24/.00/.25. Thus its high early herd converts directly to high WATER plus service allocation, not a delayed animal plan.

| operation | held-out presence | held-out exact count | MAE |
|---|---:|---:|---:|
| PLANT | 78.2% | 74.6% | .314 |
| WATER | 84.3% | 46.7% | .767 |
| HARVEST | 75.8% | 61.0% | .514 |
| CARE | 71.7% | 64.0% | .450 |
| FEED | 73.1% | 65.5% | .425 |
| FERTILIZE | 79.3% | 77.1% | .285 |
| COLLECT_FERTILIZER | 73.9% | 62.8% | .480 |

Calendar presence generalises, but exact WATER is only 46.7%, reinforcing that raw path/state reconstruction is needed before calling this a clone.

## DSM

103 full trajectories; development 1–82, held-out 83–103. DSM is a close production-family relative of M&M&P&Q, with an earlier first strawberry sowing, one fewer goose, and a d13 sheep jump.

| days | explicit crop rule | median day-start state (S/C/M/T/W) |
|---|---|---|
| d0–2 | bootstrap **6 MELON + 12 WHEAT**; finish MELON d1 and start STRAWBERRY d2 | d2 0/0/8/0/12 |
| d3–6 | early STRAWBERRY build, d6 second S+MELON fill | d7 20/0/12/0/3 |
| d8–16 | replant WHEAT every date; build STRAWBERRY to 28, with only small CARROT/TOMATO probes | d14 27/0/4/0/19; d16 28/0/4/0/17 |
| d17–22 | steady STRAWBERRY→CARROT conversion while WHEAT stays about 20–23 | d22 20/10/0/0/23 |
| d23–27 | finish CARROT rotation, leave a larger residual S than M&M&P&Q | d25 9/15/0/0/32; d27 7/20/0/0/27 |

All 82 development trajectories add MELON/WHEAT d0, STRAWBERRY d2–3, and (81/82) a d6 STRAWBERRY fill (median +12). WHEAT refill is effectively universal d8, d10–11, d14, d17–19 and d21–25. CARROT starts as probes d10–16, becomes the terminal rule d17 onward (70/82 add d22; 71/82 d23; 75/82 d24–26). Thus DSM's notable crop distinction is keeping a much larger strawberry base through d28 (median 7), versus M&M&P&Q's 3.

Herd/structure rule: d1 is 5 PASTURE and **2 COW/3 SHEEP**; d5 8 pasture and 5/3/0; d7 12 pasture and 6/3/0. COOP/geese begin d8 (12/1), reach 12/4 with 6/3/4 d9, then 14/6 and **7 COW/3 SHEEP/6 GOOSE** d10. Sheep jump to 7 on d13; the 7/7/6 herd holds through d22, then runs down to 6/4/6. It is high-herd as M&M&P&Q but has a stable 6, not 7, geese.

Fertilizer starts d11 (median 5), rises to 9/11/16 d12–14 and 24–28 d16 onward: same `post-d10, fertilize most standing crop tiles` policy as M&M&P&Q.

At herd≥10, mean units/turn are WATER 1.76, HARVEST .90, CARE .64, FEED .65, FERTILIZE .39, COLLECT_FERTILIZER .78 (58,553 turns); at herd 1–9 they are .58/.12/.26/.23/.00/.24. This again ties production allocation to early herd size.

| operation | held-out presence | held-out exact count | MAE |
|---|---:|---:|---:|
| PLANT | 79.8% | 76.2% | .290 |
| WATER | 88.7% | 52.3% | .692 |
| HARVEST | 78.8% | 63.0% | .485 |
| CARE | 77.3% | 68.7% | .371 |
| FEED | 77.3% | 69.0% | .365 |
| FERTILIZE | 79.7% | 77.6% | .282 |
| COLLECT_FERTILIZER | 77.9% | 67.3% | .409 |

## fuxi

Pending completed decision log.
