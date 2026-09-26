# T034 — reactive ladder class

_2026-09-26, Codex. Kaggle was used read-only; no submission was made._

## Scope and reproducible data

`ladder_two_classes.md` classified 9 of 39 losses in the 80-game es3_g5
window as own-route (`<50%` identical d9--29 position frames), versus 70
tape-clones in the full 80-game cohort.  The classifier was re-run directly
on replay observations, yielding the nine files in
`research/t034_reactive/reactive_losses_classified.json`; detailed daily
records for both players are `research/t034_reactive/losses_9.jsonl`.

For current behaviour, read-only Kaggle `team-submissions` / `episodes` /
`replay` fetched the first 20 completed episodes from **each** current active
submission (40/team, 160 total):

| team | active submissions | current episodes |
|---|---:|---:|
| fuxi | 56494377, 56494372 | 40 |
| istinetz | 56546676, 56520762 | 40 |
| Joseph Adamski | 56557382, 56524217 | 40 |
| Варим сельский самогон | 56571988, 56552000 | 40 |

Raw replays are in `replays/reactive/<team>/`. `episodes.jsonl` and
`summary.json` under `research/t034_reactive/` are the full 30-day, two-sided
timeline and aggregate. They were re-executed with the installed official
engine using at most eight processes. `hires` is successful seasonal hire
count that day; day-boundary `hands` is deliberately not used because hands
are fired nightly. Crop/herd counts are end-of-day tiles. Sales have exact
successful units and shared-market commit prices. Fertilizer's per-day column
is declared `FERTILIZE`; its successful seasonal total comes from the engine
hook (the replay's worker-array index is not a stable inventory identity).

## The exact nine Horizon losses

| reactive player | replay file | margin vs us | reactive land days | ours |
|---|---|---:|---|---|
| fuxi | 113496178 | +$12,939 | d6, d10 | d6, d11 |
| fuxi | 113575960 | +$17,738 | **d5, d9, d10** | d6, d11 |
| Joseph Adamski | 113584056 | +$11,037 | d7, d10 | d6, d11 |
| istinetz | 113636123 | +$5,656 | d6, d9 | d6, d11 |
| Варим сельский самогон | 113631813 | +$2,603 | d5, d11 | d6, d11 |
| 我小栗帽要娶藤正进行曲！！！💍 | 113425111 | +$2,404 | d6, d11 | d6, d11 |
| We wanna be tomatos | 113446092 | +$697 | d6, d9 | d6, d11 |
| Breaking1800 | 113506066 | +$1,585 | d6, d9, d10 | d6, d11, d18 |
| Một hai ba bốn 5 sáu bảy tám 9 | 113479719 | +$1,213 | d6, d11 | d6, d11 |

The compact mean timeline below is the reactive side / Horizon side over all
nine. Columns are: unlocked land, daily hires, COW/SHEEP/GOOSE, then
WHEAT/CARROT/TOMATO/STRAWBERRY/MELON tiles. The full per-day series including
sales and declared fertilizer is in `losses_9.jsonl`.

| EOD day | land | hires | herd C/S/G | crops W/Ca/T/St/M |
|---:|---:|---:|---:|---:|
| 3 | 1.0 / 1.0 | 4.7 / 5.0 | 3.6/2.6/0.1 — 4.0/2.0/0.0 | 7.9/0/0/2.7/8.1 — 7/0/0/0/12 |
| 6 | 1.9 / 2.0 | 6.7 / 7.3 | 4.7/4.3/0.6 — 4.7/2.7/0.7 | 7.0/.7/.2/13.4/9.1 — 4.8/.2/0/12/12 |
| 10 | **2.9 / 2.0** | 11.1 / 11.0 | 7.2/7.0/2.7 — 7.3/7.1/1.6 | 18.7/1.2/.7/22.0/3.6 — 12/0/0/20/0 |
| 15 | 3.2 / 3.0 | 11.3 / 10.3 | 7.4/7.3/3.1 — 7.6/7.4/2.0 | 19/3/3.6/31.6/3 — 24.1/.2/0/33/0 |
| 20 | 3.2 / 3.1 | 11.3 / 11.4 | 7.1/6.2/3.1 — 7.6/7.4/2.0 | 17.1/2.7/**9.8**/28.9/3.6 — 24.8/.2/1.1/33/0 |
| 25 | 3.2 / 3.1 | 11.8 / 11.4 | 6.8/5.2/3.1 — 7.6/7.4/2.0 | 19.2/17.6/7.6/11.7/2.1 — 26/19/1.1/13/0 |

Fertilization is a real scale difference, not an opening signal: successful
`FERTILIZE` totals are **154.6 versus 107.6** per game; declared activity
starts materially at d11 on reactive routes, versus d13 on Horizon. Aggregate
sales show the financial consequence:

| item | reactive units, $/unit | Horizon units, $/unit |
|---|---:|---:|
| strawberry | 233, **$150.0** | 247, $129.4 |
| milk | 194, **$128.5** | 212, $122.3 |
| wheat | 805, $38.4 | 884, $40.8 |
| tomato | **79, $80.1** | 9, $100.9 |
| egg | **106, $50.0** | 65, $49.8 |
| fertilizer | 307, $47.9 | 331, $45.2 |

This is not proof that a reactive player foresaw our order: sales are an
endogenous shared-market outcome. It **does** reject the explanation that they
simply produce more of the same Horizon mix: they sell fewer strawberries and
less wheat yet realize about $3.0k more from strawberry price, $1.2k more from
milk price, $5.4k more tomato revenue and $2.0k more egg revenue in this
loss-only cohort.

## What is repeatable in the four current samples

These 160 games are against their actual contemporary opponents, not against
our submission; they identify stable route families rather than causal
Horizon-minus-reactive effects.

* **fuxi** is the strongest land-expander: mean 2.58 land at d8 and 3.45 at
  d11 (opponents 2.10/3.10); it has 15.3 strawberry tiles at d8, 23.4 at d11,
  reaches 3.2 geese, and keeps a tomato lane after d15. It averages 3.83 land
  by d15, including frequent fourth land.
* **istinetz** is a three-land, heavy-WHEAT turnover route: 1,866 wheat sold
  ($67.9k) versus its actual opponents' 1,091 ($41.5k), then switches d20--25
  into carrot (11.4→22.1 tiles). It is not just our strawberry tape.
* **Joseph Adamski** is the clearest pure turnover route: 3,212 wheat sold
  ($116.1k), 2.75× opponent volume, while retaining roughly 8 cows, 6 sheep
  and 3--4 geese. It delays hires early (d3 3.0 vs opponent 5.1) then catches
  up, so the edge is allocation and market flow, not a generic “hire more”.
* **Варим сельский самогон** is closest to a stable capacity macro: second
  land d5, 7.8 cows / 7.5 sheep by d15, ≈34 strawberry tiles d11--20, and
  three land by d11. Its contemporary mean margin is negative ($−1.2k), so it
  is evidence for the d5 land timing but not a generally stronger opponent.

## Ranked mechanisms and es7_wm counter-modules

1. **Advance the third-land decision, with real route ownership.** Six of nine
   reactive losses take third land d9--10 while Horizon takes it d11; fuxi and
   Breaking1800 also take fourth d10. This is the clearest temporal divergence
   and buys the tile capacity for tomato/carrots/extra geese. A candidate must
   be a default-off `land_d9_route` module, allowed only when the existing
   route has enough cash and it owns the BUY_LAND, access, crop/animal placement
   and service path. A bare earlier BUY_LAND order is not a counter-module.
2. **Replace part of the fixed late crop mix with a route-owned tomato + goose
   lane.** At d20 the loss cohort has 9.8 tomato tiles and 3.1 geese versus
   Horizon's 1.1 and 2.0; it realizes +$5.4k tomato and +$2.0k egg revenue.
   The correct experiment is not the already-rejected d0 tomato-for-cow G2:
   it is a default-off d12--15 lane conditional on acquired third land and a
   genuinely idle worker/cell, owning plant/water/harvest/drop. It must abort
   on any parent trace mismatch.
3. **Observed supply/price response for existing strawberry and milk sales.**
   The loss cohort earns +$20.6 per strawberry despite 14 fewer units and
   +$6.2 per milk. Test only a bounded, default-off sell-slot deferral/advance
   of an already-scheduled own sale after observed rival mature stock/recent
   sale evidence; no new purchases or movement. T032's advance-only harvest
   forecast had cash but no score evidence, so this is a falsifiable
   broadened hypothesis, not a promotion claim. The data cannot yet distinguish
   deliberate exploitation of Horizon's predictable sales from general route
   timing.

All three require a new gate against a real own-route controller. A clone-only
panel cannot establish this barrier is fixed.

## Can one be copied into a local stand-in?

No, not from defensible public evidence. Read-only Kaggle code searches were
made with exact team names and each listed member account (`padyue`,
`pytorch5009asd`, `istinetz`, `josephadamski91`, `andrey4522`, `asimandia`,
`darksteeldragon`, `evgeniyveselkov`, `ispromashka`) constrained to
`--competition kaggriculture`; account searches returned `Not found`, and
exact-name search returned only unrelated notebooks. Generic `reactive` search
returns public Özer/Yaxon/Thomas-style controllers, but none is attributable
to these submissions. Replays reveal behaviour but are not source code and
their frozen tapes are known to break on foreign seeds. Therefore there is no
honest copyable strong local stand-in yet; do not relabel a public notebook as
fuxi/Joseph/istinetz/«самогон».

The reproducible local tool is `lab/tools/reactive_census.py` (commit
`9fa7558`); it performs no network operation and needs only downloaded replay
JSONs.
