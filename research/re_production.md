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

### Spatial audit from raw actions

The aggregate log intentionally drops coordinates, so a separate raw-action audit was made on 10 replay trajectories per team. Coordinates are farm `(row,column)` before the action; crop/land geometry is stable enough to infer blocks, but exact within-block tile order is not invariant across episodes.

| family/team | initial 5×5 block (d0–4) | block `(5:9,0:4)` at d6 | block `(0:4,5:9)` at d8 |
|---|---|---|---|
| Boey | WHEAT/MELON mix, then STRAWBERRY replaces openings | predominantly STRAWBERRY | predominantly WHEAT |
| M&M&P&Q | WHEAT/MELON mix, then STRAWBERRY replaces openings | predominantly STRAWBERRY (with edge MELON/WHEAT) | predominantly WHEAT |
| DSM | WHEAT/MELON mix, STRAWBERRY starts d2 | STRAWBERRY plus larger MELON/WHEAT edge mix | predominantly WHEAT |
| fuxi | WHEAT-dominant d0; CARROT/MELON already present | WHEAT-dominant, with some S/C | WHEAT plus CARROT; no berry-only block |

For example, in the 10-replay Boey audit d6 plant actions at `(7:9,1:4)` are overwhelmingly STRAWBERRY (136 S versus 14 M and 48 W total that day), while d8 actions in the lower-left block are 90 W. M&M&P&Q is still clearer (d6: 150 S; d8: 137 W). This gives a usable first layout rule for top-RE: allocate the second unlocked quadrant to berry production and third to wheat for the M&M&P&Q/DSM/Boey family; fuxi requires its own mixed-block policy. Do not hard-code a coordinate ordering within a block yet.

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

### d0–d10 fixed-opening falsification (M&M&P&Q + DSM)

The requested direct test rejects the premise that these two teams share a deterministic early tape. On each team separately, use the first 75% of complete trajectories to take the per-step modal vector and predict all 240 d0–d9 turns of the held-out 25%. A full vector includes moves and all unit operations; the production vector includes `PICKUP, PLACE, BUILD_PASTURE, BUILD_COOP, PLANT, WATER, HARVEST, CARE, FEED, FERTILIZE, COLLECT_FERTILIZER`.

| teacher | held-out exact full vector | held-out exact production vector |
|---|---:|---:|
| M&M&P&Q | 756/8,160 = **9.3%** | 1,500/8,160 = **18.4%** |
| DSM | 2,220/6,240 = **35.6%** | 2,769/6,240 = **44.4%** |
| pooled M&M&P&Q + DSM production template |  | 4,401/14,400 = **30.6%** |

The common *state milestones* are real (d1 2C/3S and 5 pasture; d5 about 5C/3S and 8 pasture; d10 7C/3S/7G with 13 pasture/7 coop for M&M&P&Q, versus 7C/3S/6G with 13–14 pasture/6 coop for DSM), but their action timings, pathing and goose/coop pace are not a shared fixed opening. A fixed d0–d8 tape graft is therefore rejected before implementation. The only defensible feasibility experiment is a **state-gated d8+** module (e.g. conditional capacity/service once existing Horizon land and cash permit), with an identity-off check and a new screen; it must not claim to reproduce either top agent's early route.

Feasibility disposition: do not re-run a cosmetic variant of the only existing tape-safe herd conversion. `lab/hplus/goose_microplan.py` can change a certified **d0–d3** Horizon COW/SHEEP pickup/build/place route to GOOSE/COOP, but it has no native d8 chain. Its first two-goose/cow-only leg was already rejected in T028's fresh both-seat capability screen (0/8, −$2,581). Coupled with the fixed-opening falsification above, there is no evidence-supported state-gated d8+ herd module to implement from the current parent tape. A free-moving d8 worker would be a new planner, not a reconstruction; reserve it for the separate top-RE opponent rather than claim it as a Horizon graft.

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

40 full trajectories; development 1–32, held-out 33–40. fuxi is not the M&M&P&Q/DSM monoculture-to-terminal-CARROT family. It runs a diversified five-crop production plan, including the tomato lane identified in reactive-loss audits.

| days | explicit crop rule | median day-start state (S/C/M/T/W) |
|---|---|---|
| d0–3 | bootstrap **15 WHEAT + 2 CARROT + 1 MELON**; no strawberry yet | d1 0/2/1/0/15 |
| d4–7 | add STRAWBERRY+MELON (d4) and restore WHEAT; no single-crop replacement | d5 4/0/5/0/3; d7 6/0/5/0/14 |
| d8–13 | build all crop lanes, especially STRAWBERRY; WHEAT stays 17–22 | d13 29/2/12/2/22 |
| d14–18 | begin fertilizer and scale TOMATO hard while S peaks 31–34 | d16 34/2/9/6/20; d18 33/1/8/13/13 |
| d19–24 | maintain **16 TOMATO** and ≈33 STRAWBERRY alongside WHEAT/CARROT/MELON | d21 33/2/7/16/15 |
| d25–29 | only then run down strawberry/tomato and re-fill CARROT/WHEAT | d27 11/10/3/12/18 |

The state transition test makes the schedule concrete: all 32 development trajectories add WHEAT=15 on d0, 30/32 add CARROT=2 and 26/32 MELON=1. On d4, 31/32 add STRAWBERRY (median +4) and all 32 add MELON (median +3). TOMATO is not an incidental response: additions occur in 28/32, 29/32 and 30/32 trajectories on d16/d17/d18; the standing median then reaches 16 on d19–24. Late CARROT/WHEAT filling resumes most strongly d25 (27/32 and 28/32). This is the current direct production explanation for fuxi's tomato volume, although targets and the decision to react to an opponent still need raw-state attribution.

Herd/structure rule: d1 is 6 PASTURE and **3 COW/3 SHEEP**; d6 10 pasture and 6/3/0; d8 begins a COOP/goose lane (11/1 and 7/4/1). By d10 it is 12/3 with 8/4/3, and d13 reaches 13 PASTURE/3 COOP with **8 COW/4 SHEEP/3 GOOSE**. This peak is then held to d18 before a controlled rundown to 6/3/3. It has a smaller herd than M&M&P&Q/DSM but much larger simultaneous crop surface.

Fertilizer begins later than the other two high-herd teams (d14: 6, d15: 9, d17: 18), then deliberately supports 25–31 fertile tiles d20–27. Current explicit rule: `do not fertilize before the diversified crop expansion; begin at d14, strengthen the tomato/strawberry phase through d27`.

At herd≥10, mean units/turn are WATER **2.03**, HARVEST .86, CARE .49, FEED .53, FERTILIZE .23 and COLLECT_FERTILIZER .60 (20,525 turns); at herd 1–9 they are 1.24/.44/.25/.26/.08/.28. Relative to M&M&P&Q/DSM this confirms the allocation trade: more worker capacity goes to crop WATER, less to animal service.

| operation | held-out presence | held-out exact count | MAE |
|---|---:|---:|---:|
| PLANT | 76.6% | 76.1% | .325 |
| WATER | 81.9% | 39.3% | 1.005 |
| HARVEST | 72.6% | 58.6% | .581 |
| CARE | 68.5% | 66.5% | .417 |
| FEED | 66.9% | 64.4% | .445 |
| FERTILIZE | 85.2% | 85.1% | .193 |
| COLLECT_FERTILIZER | 65.8% | 61.8% | .477 |

The small held-out set (8 trajectories) means these are descriptive agreement measurements, not a final generalisation claim. Exact WATER is especially poor because the diversified crop plan requires state/position-aware dispatch; raw target reconstruction is mandatory for top-RE.
