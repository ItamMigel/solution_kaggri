# Kaggriculture — exhaustive reimplementation specification (WP1)

**Authority.** Every statement below is derived from
`/venv/main/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py`
(1054 lines, referenced as `sim:NNN`) and
`/venv/main/lib/python3.12/site-packages/kaggle_environments/core.py` (referenced as `core:NNN`),
plus `kaggriculture.json` (the spec/config defaults, `json:key`).
`competition/raw/README.md`, `AGENTS.md` and `research/KNOWLEDGE.md` are **not** authority — several
statements in them are wrong (see §17). If this document and the source disagree, the source wins and
this document is a bug.

Everything here was read from the source; the items marked **[verified]** were additionally confirmed by
executing the real simulator (probe scripts, this session).

Target audience: someone implementing a batched reimplementation **from this document alone**.

---

## 0. Configuration

All defaults from `json:configuration`. The GPU env only ever needs the defaults; they are hard-coded
constants, but the source reads them from config, so the citation trail mentions both.

| key | default | used at |
|---|---|---|
| `episodeSteps` | 720 | `sim:928` |
| `boardSize` | 10 | `sim:236` |
| `startingMoney` | 3000 | `sim:237` |
| `maxMarketOrdersPerTurn` | 10 | `sim:526` |
| `turnsPerDay` | 24 | `sim:874` |
| `shedCapacity` | 100 | `sim:876` |
| `weedSpawnChance` | 0.005 | `sim:834` |
| `townShopUnlockInterval` | 3 | `sim:836` |
| `townShopSellInterval` | 4 | `sim:701` |
| `townCenterSellInterval` | 12 | `sim:702` |
| `farmHandCostMult` | 1 | `sim:527` |
| `seed` | null → random 31-bit | `core:199-229` |
| `actTimeout` | 1 s | irrelevant to the GPU env |

Derived constants used throughout: `HALF = 5`, `SHED_ACCESS = {(4,4),(5,4),(4,5),(5,5)}` as `(x,y)`
(`sim:117-124`), `TURNS = 24`, `DAYS = 30`.

---

## 1. Time structure  **[verified]**

- One episode = **720 recorded states** (`env.steps[0..719]`) and **719 interpreter calls**
  (= 719 agent decisions), at `step = 0 .. 718`.
- `env.steps[t].observation.step == t` (`core:626`). `steps[0]` is the post-`_initialize` state with no
  action. The action recorded in `steps[t]` (t ≥ 1) is the action that was applied **at interpreter step
  `t-1`**, transforming `steps[t-1]` into `steps[t]`.
- Inside the interpreter, `step = obs0.step` is the **pre-increment** step (`sim:878`) and
  `day = step // 24` (`sim:879`), `hour = step % 24`.
- End-of-day fires when `(step + 1) % 24 == 0` (`sim:913`), i.e. at `step ∈ {23, 47, …, 695}` — the last
  one is `step 695`, closing **day 28**.
- **Day 29 has no end-of-day.** `step 719` (which would close day 29) is never executed, because the
  episode terminates on `step 718`. Consequently, on day 29: no plant refresh, no animal production, no
  weed spawn, **no auto-drop of unit inventories into the shed**, no farmer/hand reset, no shop unlock.
  Anything sitting in a unit inventory or on a tile at the end of day 29 is worth **nothing**.
  ⇒ Last actionable step = **718** (day 29, hour 22). `steps[719]` reports day 29 hour 23 but no action
  was ever taken there.
- Termination (`sim:928-931`): after processing, `if step >= episodeSteps - 2` (i.e. `step >= 718`),
  every agent gets `status = "DONE"` and `reward = float(farms[player]["money"])`.

**Step pipeline (exact order, `sim:862-933`).** Per interpreter call:

1. **Unit actions**, player 0 fully then player 1 (`sim:881-907`):
   for player *i*: compute the PLANT seed block (§4.0), then apply the farmer action (unit index 0),
   then each hand action in list order (unit indices 1, 2, …).
2. `_process_market(state, env)` — §5.
3. `_town_consume(env, state, step)` — §6.
4. `_decay_plants(farm, step)` for farm 0 then farm 1 — §7.
5. if `(step + 1) % 24 == 0`: `_end_of_day(state, env, day)` — §8.
6. `obs.day = (step+1)//24`, `obs.hour = (step+1)%24`.
7. termination check.

This ordering is **semantics**, not detail. In particular: unit actions of *both* players complete before
*any* market order of *either* player is evaluated; the market runs before the town drains; plant decay
runs after the market (so a plant that decays this step could still have been harvested and sold this
step); and end-of-day runs after everything.

---

## 2. Initial state (`sim:127-160`, `sim:229-261`)

Per player:
- `money = 3000.0` (a Python float, but always integral — see §12).
- `tiles[y][x] = None` if `quadrant(x,y) == "NW"` else `"LOCKED"` (`sim:142-143`).
  `quadrant(x,y) = ("N" if y<5 else "S") + ("W" if x<5 else "E")` (`sim:112-114`).
- `farmer = (4,4)` — the first shed-access tile in NW (`sim:146-151`).
- `hands = []`, `unlocked_quadrants = ["NW"]`, `hires_today = 0`.
- `shed = {item: 0}` over the 9 PRODUCTS **plus the 3 ANIMALS** (`sim:156`) — 12 keys; animals held in
  the shed count against `shedCapacity`.
- `seeds = {crop: 0}` over the 5 crops.
- `inventories = [{}]` (index 0 = farmer; hands appended on hire).

Shared:
- `market.inventory[item] = 10000` for all 9 products; `market.prices[item] = base` (`sim:165-166`).
- `town.unlocked_shops = []`.
- `day = 0`, `hour = 0`.

---

## 3. Item / crop / animal tables

```
PRODUCTS (order fixed, sim:25) = [WHEAT, CARROT, TOMATO, STRAWBERRY, MELON, EGG, MILK, WOOL, FERTILIZER]
ANIMALS  (order fixed, sim:19) = [GOOSE, COW, SHEEP]
CROPS    (order fixed, sim:11) = [WHEAT, CARROT, TOMATO, STRAWBERRY, MELON]   # == PRODUCTS[0:5]
```

**Crops** (`sim:11-17`):

| crop | seed cost | first_yield_day | max_yield_day | interval | max_yield | ongoing |
|---|---|---|---|---|---|---|
| WHEAT | 10 | 2 | 4 | 0 | 6 | no |
| CARROT | 20 | 2 | 3 | 0 | 4 | no |
| TOMATO | 50 | 8 | 8 | 1 | 4 | yes |
| STRAWBERRY | 100 | 10 | 10 | 2 | 4 | yes |
| MELON | 80 | 10 | 12 | 0 | 6 | no |

**Animals** (`sim:19-23`):

| animal | cost | structure | first_yield_day | interval | max_held | product |
|---|---|---|---|---|---|---|
| GOOSE | 300 | COOP | 4 | 1 | 4 | EGG |
| COW | 400 | PASTURE | 8 | 2 | 6 | MILK |
| SHEEP | 500 | PASTURE | 6 | 3 | 6 | WOOL |

**Market params** (`sim:40-50`), all with `I0 = 10000`, `PRICE_FLOOR = 1`:

| item | base | T | below_func | below_target | above_func | above_target |
|---|---|---|---|---|---|---|
| WHEAT | 25 | 400 | sqrt | 0.80 | log | 0.20 |
| CARROT | 35 | 450 | log | 0.20 | sqrt | 0.70 |
| TOMATO | 60 | 200 | linear | 0.40 | sqrt | 0.60 |
| STRAWBERRY | 120 | 100 | sqrt | 0.70 | linear | 1.60 |
| MELON | 250 | 300 | log | 0.20 | sq | 3.60 |
| EGG | 50 | 332 | linear | 0.40 | log | 0.20 |
| MILK | 160 | 122 | sqrt | 0.60 | linear | 1.60 |
| WOOL | 200 | 105 | log | 0.20 | sq | 3.20 |
| FERTILIZER | 100 | 200 | linear | 0.40 | linear | 0.40 |

**Shops** (`sim:89-98`, order fixed — it is the iteration order of `SHOPS`):

```
0 BAKERY         [EGG, WHEAT]
1 PIZZA_SHOP     [MILK, TOMATO, WHEAT]
2 BRUNCH_SPOT    [EGG, WHEAT, STRAWBERRY]
3 YARN_STORE     [WOOL]                                   # single-product -> x2
4 ICE_CREAM_SHOP [STRAWBERRY, MILK, WHEAT]
5 PET_CAFE       [CARROT]                                  # single-product -> x2
6 SMOOTHIE_SHOP  [STRAWBERRY, MILK]
7 FARMERS_MARKET [WHEAT, CARROT, TOMATO, STRAWBERRY]
```

`TOWN_CENTER_PRODUCTS = PRODUCTS \ {FERTILIZER}` (`sim:100`) — **fertilizer has no town sink at all**.

---

## 4. Unit actions (`_apply_unit_action`, `sim:297-505`)

**Every invalid / illegal action is a silent no-op.** There is no penalty, no cost, no message.

### 4.0 Pre-validation: the atomic PLANT block (`sim:888-901`)

Per player, **before any of that player's units act**:
- collect `unit_actions = [farmer_action, *hands_actions]` — note this includes hand slots that do
  **not** correspond to an existing hand;
- `plant_demand[crop] = #{a : a[0]=="PLANT" and len(a)>=2 and a[1]==crop}`;
- `blocked = {crop : plant_demand[crop] > seeds[crop]}`;
- every action `["PLANT", c]` with `c ∈ blocked` is replaced by `["PASS"]` — **all of them**, not just
  the excess.

⚠️ **Surprise:** PLANT requests issued for non-existent hands still count toward `plant_demand`, so a
padded action list can cancel the farmer's own PLANT. (The GPU env must count PLANT ops over all
`MAX_HANDS` slots that the policy actually emitted; padding slots with `PASS` is safe — see §14.)

### 4.1 Common prologue (`sim:299-323`)

```
if action is not a non-empty list: no-op                       # empty list == PASS
op = action[0]
pos = unit position; if the unit does not exist (idx-1 >= len(hands)): no-op   # sim:263-267
if op in {NORTH,SOUTH,EAST,WEST}: <move>; return
if op == PASS: return
tile = tiles[fy][fx]
if tile == "LOCKED": return                                    # blocks EVERY non-move op
```

⚠️ The LOCKED check is on the tile the unit is **standing on**, and it happens *after* the movement
branch. A unit standing on a locked tile can still move out, but can do nothing else. Hands can spawn on
locked tiles (§11.1), so this case really occurs.

### 4.2 Movement (`sim:308-316`)

`NORTH=(0,-1) SOUTH=(0,+1) EAST=(+1,0) WEST=(-1,0)` (`sim:74-79`; y grows downward).
Move fails (no-op) if the target is off-board or the **target** tile is `"LOCKED"`.
One tile per action, no cost, no speed modifier. A unit therefore moves at most 1 tile per step, and any
tile of the 10×10 board is at most 18 steps away.

### 4.3 `DROP` (`sim:325-338`)

- requires `(fx,fy) ∈ SHED_ACCESS`, else no-op;
- for **each** item in the unit inventory (dict iteration order = insertion order):
  `room = max(0, 100 - sum(shed.values()))`, `take = min(n, room)`, `shed[item] += take`,
  and then **`del inv[item]` unconditionally**.
- ⇒ **overflow is destroyed, not left in the inventory.** `sum(shed.values())` counts products *and*
  animals held in the shed.
- Takes no arguments; drops everything the unit carries.
- ⚠️ Because room is recomputed per item, the *first* items in insertion order get the space.

### 4.4 `PICKUP <item> [n=1]` (`sim:340-357`)

- requires shed-access tile; `len(action) >= 2`; `n = int(action[2]) if len>=3 else 1`; `n<=0` → no-op;
- `n = min(n, shed.get(item, 0))`; if 0 → no-op; else `shed[item] -= n; inv[item] += n`.
- Seeds live in `private["seeds"]` and can never be picked up (`sim:349-350`).
- The unit inventory has **no capacity limit**.

### 4.5 `PLANT <crop>` (`sim:359-371`)

Requires `crop ∈ CROPS`, `tile is None`, `seeds[crop] > 0`. Then `seeds[crop] -= 1` and the tile becomes
a new plant (`_new_plant`, `sim:200-211`):
```
kind=PLANT, crop, planted_day=day, watered_today=False,
consecutive_unwatered = 1,                    # planting day counts as unwatered
yield_units = 0 if ongoing else 1,
max_lifespan_step = -1 if ongoing else (day + max_yield_day + 1) * 24,
fertilized_until_day = -1
```
⚠️ **`consecutive_unwatered` starts at 1**: a crop that is *not* watered on its planting day reaches 2 at
that same end-of-day and dies immediately (§8.1). Watering on the planting day is mandatory. (This
qualifies the "survives one dry day" rule — it does, but only *after* the first watering.)

### 4.6 `WATER` (`sim:373-386`)

Requires a PLANT tile, `watered_today == False`. Sets `watered_today = True`.
Then, **for non-ongoing crops only**:
```
age = day - planted_day
window_start = (max_yield_day + 1) // 2
if window_start <= age <= max_yield_day:
    bonus = 2 if fertilized_until_day >= day else 1
    yield_units = min(max_yield, yield_units + bonus)
```
Windows: WHEAT days 2..4 (start 1, max 6), CARROT 2..3 (start 1, max 4), MELON 6..12 (start 1, max 6).
Watering outside the window is legal but adds nothing (it still counts against death).
Ongoing crops (TOMATO/STRAWBERRY) gain nothing at WATER time; their production is at end-of-day (§8.1).

### 4.7 `HARVEST` (`sim:388-415`)

Requires a dict tile with `yield_units > 0`.
- PLANT: additionally requires `day - planted_day >= first_yield_day` (else no-op; for ongoing crops the
  source prints a warning that "should never happen"). Then `inv[crop] += yield_units`,
  `yield_units = 0`, and **for non-ongoing crops the tile becomes `None`** (the plant is consumed).
  Ongoing crops keep growing.
- Animal tile: `inv[product] += yield_units`, `yield_units = 0`. Structure and animal stay.

### 4.8 `FERTILIZE` (`sim:417-424`)

Requires a PLANT tile and consumes 1 `FERTILIZER` from the **unit's** inventory. Then
`fertilized_until_day = max(fertilized_until_day, day + 2)` — active on `day`, `day+1`, `day+2`
(checks are `fertilized_until_day >= day`, `sim:384`, and `>= current_day`, `sim:768`).

### 4.9 `DIG` (`sim:426-433`)

`tile is None` → no-op. A tile **with an animal** → no-op. Anything else (plant, weed, empty
COOP/PASTURE) → tile becomes `None`. Free.

### 4.10 `BUILD_COOP` / `BUILD_PASTURE` (`sim:435-445`)

Requires `tile is None`. Sets `tiles[fy][fx] = {"kind": "COOP"|"PASTURE"}`. **Free** — building costs
nothing.

### 4.11 `PLACE <item> [n=1]` (`sim:447-478`)

Two disjoint branches:
1. **Animal placement.** If `item ∈ ANIMALS` **and** the tile is a dict with `kind == structure(item)`
   **and** the tile has no animal: try `inv.take(item, 1)`; on success the tile becomes a new animal
   (`_new_animal`, `sim:214-226`):
   `kind=structure, animal, placed_day=day, yield_units=0, consecutive_unfed=0, fed_today=False,
   cared_today=False, fertilizer_available=False, pending_care_bonus=0`.
   **This branch returns unconditionally** — if the unit does not carry the animal, the action is a
   no-op; it does *not* fall through to branch 2.
2. **Partial shed drop.** Otherwise, if `(fx,fy) ∈ SHED_ACCESS`:
   `n = int(action[2]) if len>=3 else 1`; `n<=0` → no-op; `n = min(n, inv[item])`;
   `room = max(0, 100 - sum(shed.values()))`; `n = min(n, room)`; if `n<=0` no-op;
   else move `n` from inventory to shed.
   ⚠️ Unlike `DROP`, `PLACE` **does not destroy** what does not fit.

### 4.12 `FEED` (`sim:480-488`)

Requires an animal tile with `fed_today == False`, and consumes **1 WHEAT from the unit's own
inventory** (`_inv_take(inv,"WHEAT",1)`), not from the shed. ⇒ a unit must first `PICKUP WHEAT n` while
standing on a shed-access tile, then walk to the animal. Sets `fed_today = True`.

### 4.13 `COLLECT_FERTILIZER` (`sim:490-497`)

Requires an animal tile with `fertilizer_available == True`. Clears the flag and adds 1 `FERTILIZER` to
the unit inventory. The flag is set unconditionally for every surviving animal at every end-of-day
(`sim:800`) — **no CARE and no feeding required**; a newly placed animal has it `False` until its first
end-of-day. Effectively 1 free fertilizer per animal per day.

### 4.14 `CARE` (`sim:499-505`)

Requires an animal tile with `cared_today == False`. Sets `cared_today = True`. No cost, no immediate
effect; it is banked at end-of-day (§8.2).

---

## 5. Market (`_process_market`, `sim:519-602`)

Runs once per step, after all unit actions of both players.

```
queues[p] = (action["market"] if list else [])[:10]        # sim:529-534
max_len   = max(len(queues[0]), len(queues[1]))
for i in range(max_len):                                   # ORDER-INDEX LANE
    ostate[p] = parse(queues[p][i]) if i < len(queues[p]) else None
    # (a) atomic ops, in player order 0 then 1
    for p in (0,1):
        if ostate[p].type == HIRE:     do_hire(p);     ostate[p] = None
        elif ostate[p].type == BUY_LAND: do_buy_land(p); ostate[p] = None
    # (b) per-unit lockstep
    while True:
        quoted = [None, None]
        for p in (0,1):
            if ostate[p] is None or ostate[p].remaining <= 0: continue
            quote price for ONE unit at the CURRENT market inventory   # both see the same inventory
            (invalid op/item combination -> ostate[p] = None)
        if both quotes None: break
        committed_any = False
        for p in (0,1):                                    # commit in player order
            ok = commit_unit(...)                          # mutates money / shed / market inventory
            if ok: ostate[p].remaining -= 1; committed_any = True
            else:  ostate[p] = None                        # order aborts on first failure
        if not committed_any: break
    refresh_prices()                                       # after EACH lane
```

### 5.1 The index lane (the single most important undocumented mechanic) **[verified]**

The loop is over the **order index**, not over players. The order at index 0 is drained **completely**
(all its units, price falling all the way) before the order at index 1 is even quoted. Measured with both
players holding 120 MELON and $100k:

| layout | player 0 | player 1 |
|---|---|---|
| both `SELL MELON 120` at index 0 | **$13,342** | **$13,342** |
| p0 index 0, p1 index 1 (behind a `HIRE`) | **$24,317** | **$2,249** |
| p0 index 1, p1 index 0 | $2,249 | $24,317 |
| solo seller, no opponent | $24,317 | — |

`HIRE` and `BUY_LAND` **consume their lane** (they are handled in step (a) and then blanked), so padding
with them does not help — the SELL itself must be at index 0.

### 5.2 Quoting and committing (`sim:564-600`, `sim:626-655`)

- `SELL item n`: valid only if `item ∈ PRODUCTS` (animals cannot be sold — the order is killed).
  price = `market_price(item, inventory[item])`.
  commit: requires `shed[item] >= 1`; `shed[item] -= 1`; `money += price`;
  **`inventory[item] += 1` only if `price > 1`** (`sim:633-634`) — sales at the price floor do not add
  supply.
- `BUY_PRODUCT item n`: valid only for `item ∈ {WHEAT, FERTILIZER}`.
  price = `market_price(item, inventory[item] - 1)` (quoted at the *post*-buy inventory, `sim:575`).
  commit: requires `money >= price`; `money -= price`; `shed[item] += 1`; `inventory[item] -= 1`.
  ⚠️ **`BUY_PRODUCT` bypasses `shedCapacity` entirely** — nothing checks the shed total here.
- `BUY_SEED crop n`: valid for `crop ∈ CROPS`; price = `CROPS[crop]["seed"]` (fixed, market-independent).
  commit: `money -= price`; `seeds[crop] += 1`. Seeds never touch the shed and are uncapped.
- `BUY_ANIMAL animal n`: valid for `animal ∈ ANIMALS`; price = `ANIMALS[animal]["cost"]` (fixed).
  commit: `money -= price`; `shed[animal] += 1` (uncapped here, but it counts toward the cap later).
- Any other `(op, item)` combination sets `ostate[p] = None` — the whole order dies.
- All money checks are `money < price → fail` (`sim:637`, `644`, `650`), so exactly-affordable is OK.
- **Both players are quoted at the same pre-commit inventory in a given lockstep iteration**, then both
  commit. Two sellers at index 0 therefore alternate one unit at a time at identical prices.

### 5.3 Order parsing (`_parse_order`, `sim:605-623`)

- not a non-empty list → `None`.
- `["HIRE", ...]` → HIRE (extra args ignored). `["BUY_LAND", ...]` → BUY_LAND.
- `SELL / BUY_SEED / BUY_PRODUCT / BUY_ANIMAL` need `len >= 3`; `n = int(order[2])` (raises on a
  non-numeric string — the whole episode would crash); `n <= 0` → `None`.
- anything else → `None`.
- A `None` at index *i* is exactly equivalent to having no order at index *i* (both do nothing), so a
  fixed-width 10-lane action tensor with an explicit `OP_NONE` is a faithful encoding.

### 5.4 Price function (`market_price`, `sim:177-191`)

```
_shape(f, x): x = max(0.0, x); linear->x ; sq->x*x ; sqrt->sqrt(x) ; log->log(1+x) ; log10->log10(1+x)

if inventory < I0:                      # scarcity
    amp   = below_target * base / _shape(below_func, T)
    price = base + amp * _shape(below_func, I0 - inventory)
else:                                   # glut  (inventory == I0 takes this branch, price == base)
    amp   = above_target * base / _shape(above_func, T)
    price = base - amp * _shape(above_func, inventory - I0)
return max(1, int(round(price)))
```
**Arithmetic requirements for parity:** the curve must be evaluated in **float64**, and the rounding must
be Python's `round()` = **round-half-to-even** (`torch.round` is also half-to-even — good). The result is
an integer; all downstream money arithmetic is exact integers.

`_refresh_prices` (`sim:194-197`) recomputes all 9 prices from the current inventory; it is idempotent
and is called after each market lane and at the end of `_town_consume`. Because it is a pure function of
inventory, calling it a different number of times is harmless — a fixed 10-lane implementation is
equivalent to the source's `max_len` lanes.

---

## 6. Town demand (`_town_consume`, `sim:696-718`)

Called every step with the pre-increment `step`; `day = step // 24`.

```
if step % 4 == 0:                                   # hours 0,4,8,12,16,20
    for shop in unlocked_shops:                     # order irrelevant
        mult = 2 if len(SHOPS[shop]) == 1 else 1
        for item in SHOPS[shop]: inventory[item] -= mult
if step % 12 == 0:                                  # hours 0 and 12
    center_mult = 4 if day >= 20 else (2 if day >= 10 else 1)
    for item in PRODUCTS except FERTILIZER: inventory[item] -= center_mult
refresh_prices()
```

Note both fire at `step 0`, before any player can have sold anything. Market inventory may go below
`I0`, which is what makes prices rise over the season. `FERTILIZER` is drained by nothing, so its price
only ever falls (from $100) as players sell into it.

Shop unlocks happen at end-of-day — see §8.4.

---

## 7. Plant decay (`_decay_plants`, `sim:721-735`)

Every step, for each farm, for every PLANT tile:
```
mls = max_lifespan_step
if mls < 0 or step < mls:      continue
if (step - mls) % 2 != 0:      continue
yield_units -= 1
if yield_units <= 0: tile = {"kind": "WEED"}
```
So from `max_lifespan_step` onward the plant loses 1 unit every **2 steps** and turns into a weed when it
hits 0. `yield_units` can go negative only transiently (it is checked immediately).

`max_lifespan_step`:
- non-ongoing: fixed at plant time = `(planted_day + max_yield_day + 1) * 24`.
- ongoing: `-1` (immortal) until the final production, at which point end-of-day sets it to
  `(next_day + 1) * 24` (`sim:770-771`).

---

## 8. End of day (`_end_of_day`, `sim:829-859`)

Fires when `(step+1) % 24 == 0`, with `day = step // 24`. The RNG is created **once per end-of-day**:

```
rng = random.Random((env.info["seed"] * 1_000_003) ^ day)          # sim:840
for player_id in (0, 1):                                            # STRICT player order
    _daily_refresh_plants(farm, day, 24)      # 8.1
    _daily_refresh_animals(farm, day)         # 8.2
    _spawn_weeds(farm, 10, 0.005, rng)        # 8.3   <-- consumes rng
    _drop_inventories_to_shed(private, 100)   # 8.5
    farm.farmer = (4,4); farm.hands = []; farm.hires_today = 0; private.inventories = [{}]
if (day+1) % 3 == 0 and any shop remains:
    choice = rng.choice(sorted(remaining));  unlocked_shops.append(choice)   # 8.4  <-- consumes rng
```

⚠️ The same `rng` object is shared by player 0's weed spawns, player 1's weed spawns and the shop draw,
**in that order**. Player 0's board therefore shifts player 1's weed rolls. This is deterministic but it
means the two farms are *not* independent in a batched implementation — see §13.

### 8.1 `_daily_refresh_plants` (`sim:738-771`)

For each PLANT tile (row-major y then x, order irrelevant — no cross-tile effects):
```
was_watered = watered_today
consecutive_unwatered = 0 if was_watered else consecutive_unwatered + 1
watered_today = False
if consecutive_unwatered >= 2: tile = {"kind": "WEED"}; continue      # death
if not ongoing: continue
days_since_first = (day+1) - planted_day - first_yield_day
if days_since_first < 0: continue
if days_since_first % interval != 0: continue
production_count = days_since_first // interval + 1
if production_count > max_yield: continue
fertilized = was_watered and fertilized_until_day >= day              # fertilizer only on watered days
yield_units = min(max_yield, yield_units + (2 if fertilized else 1))
if production_count == max_yield: max_lifespan_step = (day+2) * 24
```
TOMATO: first production at `planted_day+8`, then every day, 4 productions. STRAWBERRY: at
`planted_day+10`, then every 2 days, 4 productions (days P+10, P+12, P+14, P+16).
Note `production_count` counts *scheduled* productions, so a fertilized double still counts as one.

### 8.2 `_daily_refresh_animals` (`sim:774-802`)

For each animal tile:
```
consecutive_unfed = 0 if fed_today else consecutive_unfed + 1
if consecutive_unfed >= 2:
    tile = {"kind": structure}          # animal ESCAPES, empty structure remains
    continue
days_since_first = (day+1) - placed_day - first_yield_day
if days_since_first >= 0 and days_since_first % interval == 0:
    bonus = pending_care_bonus if fed_today else 0        # bank is CONSUMED only if fed today
    yield_units = min(max_held, yield_units + 1 + bonus)
    pending_care_bonus = 0                                # bank is BURNED even if not fed today
if cared_today and fed_today: pending_care_bonus += 1     # applied AFTER production
fertilizer_available = True
fed_today = False; cared_today = False
```
Consequences (all confirmed against the source):
- an animal must be fed **at least every other day** or it escapes (the structure survives; a new animal
  can be placed on it later);
- `CARE` is worth `+1 unit` on the **next** production event, and only if the animal is also fed that
  day (both today, for the banking, and on the production day, for the payout);
- the bank is **not** reset on non-production days, so it accumulates across the whole gap
  (`interval` days for cows/sheep, and the whole `first_yield_day` ramp before the first production);
- ⚠️ **`max_held` truncates the FIRST production.** A cow placed on day 0 that is fed+cared every day
  banks 7 by day 7 and produces `min(6, 0 + 1 + 7) = 6` on day 8, destroying 2 units. This is
  unrecoverable: `HARVEST` cannot pre-empt it because `yield_units == 0` before the event.
- missing a feed on a production day burns the entire bank **and** yields nothing that event.
- `fertilizer_available` is set for every surviving animal every day, unconditionally.

### 8.3 `_spawn_weeds` (`sim:805-809`)

```
for y in 0..9:
  for x in 0..9:
    if tiles[y][x] is None and rng.random() < 0.005: tiles[y][x] = {"kind":"WEED"}
```
⚠️ **Python `and` short-circuits**: `rng.random()` is drawn **only for empty tiles**. The number of RNG
draws consumed therefore depends on the board. This is the crux of RNG parity (§13). Locked tiles,
plants, weeds, structures and animals consume no draws. Runs *after* the plant/animal refresh of that
same player, so a plant that just died into a weed does not get a weed roll, and a tile that a
non-ongoing plant vacated at harvest does.

### 8.4 Shop unlock (`sim:853-859`)

```
next_day = day + 1
if next_day % 3 == 0:
    remaining = [s for s in SHOPS if s not in unlocked]     # then SORTED alphabetically
    if remaining: unlocked.append(rng.choice(sorted(remaining)))
```
Unlock days (`next_day`): 3, 6, 9, 12, 15, 18, 21, 24 → **all 8 shops are unlocked by the end of day 23**;
the `next_day = 27` opportunity is a no-op. Sorted order is
`[BAKERY, BRUNCH_SPOT, FARMERS_MARKET, ICE_CREAM_SHOP, PET_CAFE, PIZZA_SHOP, SMOOTHIE_SHOP, YARN_STORE]`.

### 8.5 `_drop_inventories_to_shed` (`sim:812-826`)

Identical destruction semantics to `DROP` (§4.3), applied to **every** unit inventory in order
(farmer, hand 1, hand 2, …), each item in insertion order:
`room = max(0, 100 - sum(shed.values()))`, `take = min(n, room)`, `shed[item] += take`,
**`del inv[item]` unconditionally** ⇒ anything that does not fit is **destroyed**.

---

## 9. Economy

### 9.1 Hiring (`_do_hire`, `sim:658-677`)

```
fib: fib(0)=1, fib(1)=1, fib(2)=2, fib(3)=3, fib(4)=5, ...
cost of the (n+1)-th hire of the day = 1 * fib(hires_today)
if money < cost: silent no-op (nothing is spent, hires_today unchanged)
money -= cost; hires_today += 1; hands.append(spawn_pos); inventories.append({})
```
Cumulative cost of `n` hires in one day = `fib(n+1) - 1`: 8 hands = $54, 12 = $376, 14 = $986,
16 = $2,583, 20 = $17,710.
`hires_today` resets to 0 at every end-of-day (`sim:850`) and **all hands are dismissed** at end-of-day
(`sim:849`) — hands are a per-day rental. There is no wage, no upkeep and **no cap** on the number of
hands other than money and the 10-orders-per-turn limit (spreading `HIRE` across hours lifts that too).

**`_spawn_hand` (`sim:508-516`).** The new hand appears on the shed-access tile with the fewest current
occupants (counting the farmer and existing hands), ties broken by NWSE order
`[(4,4),(5,4),(4,5),(5,5)]`.
⚠️ **No unlocked check** — hands routinely spawn on `(5,4)`, `(4,5)`, `(5,5)`, which are LOCKED until the
corresponding quadrant is bought. Such a hand can move but can do nothing else on that tile (§4.1).

### 9.2 Land (`_do_buy_land`, `sim:680-693`)

`LAND_ORDER = ["NE","SW","SE"]`, `LAND_PRICES = [1000, 2000, 4000]` (`sim:82-83`). The n-th purchase
(n = number of extra quadrants already owned) costs `LAND_PRICES[n]` and unlocks `LAND_ORDER[n]`; the
order is **fixed**, the player cannot choose. All `"LOCKED"` tiles of that quadrant become `None`
(empty). `money < cost` or all three already bought → silent no-op.

### 9.3 Shed

Capacity 100 **total items** across the 12 shed keys (9 products + 3 animals). Enforced only in
`DROP` (destructive), `PLACE` (non-destructive) and `_drop_inventories_to_shed` (destructive).
`BUY_PRODUCT` and `BUY_ANIMAL` write into the shed with **no capacity check at all**.
Unit inventories and tiles are uncapped, so tiles are free unlimited storage — but everything left in a
unit inventory at end-of-day is either moved into the 100-slot shed or destroyed, and on day 29 there is
no end-of-day at all, so it is simply lost.

---

## 10. Scoring and termination

- `sim:928-931`: when the interpreter finishes a call with `step >= 718`, both agents get
  `status="DONE"` and `reward = float(money)`. **Unsold inventory scores nothing.**
- The contract's RL reward = `money[0] - money[1]` on the terminal step, 0 elsewhere.
- Ties are possible and common in mirror matches.
- **[verified] A crashing agent is *not* scored `None` at the end of a full episode.** When an agent
  raises, `core:636-637` sets `status = ERROR` and `reward = None` *for that step*, but the episode keeps
  running (the crashed agent is never called again — `core:175` — and its action defaults to `PASS`), and
  `sim:929-931` overwrites `status` back to `DONE` and `reward` back to the player's money on the final
  step. Measured: an agent that raises at step 100 finishes with `status DONE, reward 3000.0`.
  ⇒ **any check keyed on `reward is None` is vacuous.** See §10.1 for what actually works.

### 10.1 Crash detection — verified recipe

Failure modes and which channels survive to the end of the episode (each row measured against a
deliberately broken agent, `episodeSteps = 720`):

| channel | raise @0 | raise @100 | raise @718 | timeout | malformed return | clean |
|---|---|---|---|---|---|---|
| terminal `status` / `reward` | — | — | — | — | — | — |
| per-step `steps[t][p].status` ∈ {ERROR,TIMEOUT} | ✔ | ✔ | **—** | ✔ | — | — |
| agent stops being called (`logs` row has no `duration`) | ✔ | ✔ | **—** | ✔ | — | — |
| `logs[p]["stderr"]` contains a traceback | ✔ | ✔ | **✔** | — | — | — |

- The **terminal status/reward is always `DONE` / the player's money**, in every failure mode.
- A crash on the **final** step (718) is invisible to `status` because the interpreter rewrites it that
  same call; only `stderr` sees it.
- A **timeout** never produces `stderr` (no exception is raised inside the agent — `agent.py:220-222`
  substitutes `DeadlineExceeded` *after* the call), so only the "stopped being called" / `status`
  channels see it.
  ⇒ **the detector must be the OR of `stderr`-traceback and stopped-being-called.**
- A **malformed / schema-violating return value is not an error at all**: `process_schema` silently
  substitutes the default action `{"farmer":["PASS"],"hands":[],"market":[]}` and the agent keeps
  playing. Verified for `"a string"`, `[1,2,3]`, `None`, and `{"farmer":"PASS","hands":"nope","market":7}`
  — all produce zero signal in every channel. It is not detectable from the record and costs only that
  turn. (`status = "INVALID"` therefore appears to be unreachable for this environment's action schema.)

**Log/step alignment.** `env.logs` carries the `reset()` rows in front of the per-step rows, so the log
row for interpreter step `k` is `env.logs[len(env.logs) - (len(env.steps)-1) + k]`. Compute the offset;
do not hard-code it. Within a row, index `p` is player *p*'s log; an extra trailing entry may hold the
interpreter's own stdout/stderr (e.g. the `sim:399` HARVEST warning) — never confuse it with an agent's.

`detect_crashes(env)` in `src/gpuenv/record_vectors.py` implements exactly this.

---

## 11. RNG — exact parity **is** achievable  **[verified]**

### 11.1 What is random

Exactly two things, both inside `_end_of_day`, both from **one** `random.Random` instance per (episode,
day):

```
rng = random.Random((seed * 1_000_003) ^ day)        # seed = env.info["seed"], a 31-bit int by default
```
1. `rng.random()` — one draw per **empty** tile, for player 0's 100 tiles (row-major) then player 1's.
   Max 200 draws/day, typically far fewer.
2. `rng.choice(sorted(remaining_shops))` — one *rejection-sampled* `getrandbits` draw, only on days where
   `(day+1) % 3 == 0` and shops remain.

Nothing else in the simulator is random. Market, town, growth, decay and every action are fully
deterministic given the actions.

### 11.2 The algorithm to reproduce

CPython's `random.Random` is MT19937 with:
- **seeding**: `init_by_array(key)` where `key` is `abs(seed)` split into **little-endian 32-bit words**,
  `K = max(1, ceil(bit_length/32))` words. `init_by_array` itself starts from `init_genrand(19650218)`.
  ⚠️ **K depends on the individual seed**, so a batch of seeds with different bit-lengths cannot share one
  vectorised `init_by_array` — group the batch by K (in practice K=1 for `seed*1000003 < 2^32`, K=2 for
  typical 31-bit episode seeds).
- `random()` consumes **two** 32-bit outputs: `a = w0 >> 5`, `b = w1 >> 6`,
  `value = (a * 67108864.0 + b) / 9007199254740992.0`.
- `getrandbits(k)` for `k <= 32` consumes **one** output: `w >> (32 - k)`.
- `choice(seq)` = `seq[_randbelow(len(seq))]`, and `_randbelow(n)` is
  `k = n.bit_length(); r = getrandbits(k); while r >= n: r = getrandbits(k); return r`
  — i.e. **rejection sampling, a variable number of draws**.

Since a day consumes at most `2*200 + (a few) ` words, one MT19937 twist block (624 outputs) is *not*
always enough — allow 2 blocks (1248 words) to be safe and generate the stream lazily/blockwise.

**Verification performed (this session):** a batched numpy MT19937 written from the above reproduced
`random.Random(s).random()` bit-exactly for `s ∈ {0, 1, 42, 123456789, 2^31-1, (12345·1000003)^7,
((2^31-1)·1000003)^29, (60000·1000003)^13}` (32 draws each), `getrandbits(k)` for
`k ∈ {1,3,4,8,32}`, and `choice` for `n ∈ 1..8` after 0/5/100 preceding `random()` calls.
Then, against **live episodes** (seeds 7, 60000, 123456789, 29 end-of-days each, `pass` vs `pass`), the
predicted weed tiles and the predicted shop unlock matched the simulator **exactly on every day**.

⇒ **Verdict: seed-exact parity is achievable.** No fallback to distributional parity is required.

### 11.3 Implementation guidance for the batched env

Per end-of-day the batched env needs, for each env in the batch, a stream of MT19937 32-bit words.
Two workable strategies:

- **(recommended) Batched MT19937 in torch/numpy.** State `[B, 624] uint32`; `init_by_array` is a
  sequential loop of ~1900 iterations over the 624 slots but fully vectorised across `B`; a twist is
  ~624 vectorised steps (or 3 slice-wise ops). Cost is independent of `B`, so it is negligible at
  `B = 4096`. Do it once per day (30 times per episode).
- **CPU precompute.** At `reset`, generate `[B, 30, 1248] uint32` on the CPU (`B*30*1248*4` bytes = 614 MB
  at B=4096 — too big; per-day generation `[B,1248]` = 20 MB is fine) and upload.

Consuming the stream is the subtle part, because the draw index depends on the board:
```
empty0 = (tiles[b,0] == EMPTY)            # after plants/animals refresh of player 0
idx0   = exclusive_cumsum(empty0.flatten(row-major))            # draw index per tile
n0     = empty0.sum()
empty1 = (tiles[b,1] == EMPTY)            # after plants/animals refresh of player 1
idx1   = n0 + exclusive_cumsum(empty1.flatten())
n1     = empty1.sum()
u(tile) = mt_double(words[2*idx], words[2*idx+1])
weed    = empty & (u < 0.005)
shop_word_start = 2*(n0+n1)
```
Note the two farms are coupled only through `n0`, which is a scalar per env — a cumulative sum, not a
loop. The shop `choice` then does rejection sampling from `shop_word_start` (bounded loop; ≥8 iterations
is astronomically improbable but must terminate deterministically — implement it as a fixed 8-iteration
masked loop taking the first accepted draw).

`weedSpawnChance` is compared with `<` against a float64 double; do this in float64.

---

## 12. Integer arithmetic

Money is a Python `float` in the source (`sim:129`), but every quantity added to or subtracted from it is
an integer (`int(round(price))`, `CROPS[c]["seed"]`, `ANIMALS[a]["cost"]`, `LAND_PRICES`, `fib`), and the
starting value is 3000. It is therefore **exactly integral at all times** and must be stored as `int64`
in the GPU env. Values reachable in one episode are ≲ $300k, so `int32` would also do, but `int64` avoids
any thought. Market inventories are integers (start 10000, ±small), so `int32` is ample. Only the price
*curve* uses floating point (§5.4) — evaluate it in float64 and round half-to-even to an integer.

---

## 13. Action encoding (op ids) — `src/gpuenv/ops.py` is authoritative

Per CONTRACT.md, **WP2 authors `src/gpuenv/ops.py` and WP1 uses the same file.** `record_vectors.py`
imports it (falling back to the enumeration below only if the module is missing) and stamps a
fingerprint of the id maps into every `.npz`; `difftest.py` refuses to replay a corpus whose
fingerprint disagrees with the ids currently in force. So a unilateral renumbering by either side is
caught before it can silently corrupt a comparison — but it costs a re-record, so **do not renumber
without saying so.**

The ids in force (as landed by WP2, and what the current corpus is encoded with):

```python
# unit ops (farmer + hands)          # market ops
OP_PASS               = 0           MKT_NONE        = 0   # empty / unused lane
OP_NORTH              = 1           MKT_HIRE        = 1
OP_SOUTH              = 2           MKT_BUY_LAND    = 2
OP_EAST               = 3           MKT_SELL        = 3   # item = any PRODUCT 0..8
OP_WEST               = 4           MKT_BUY_PRODUCT = 4   # item ∈ {WHEAT=0, FERTILIZER=8}
OP_PLANT              = 5   # arg1 = crop item id 0..4    MKT_BUY_SEED = 5   # item = crop 0..4
OP_WATER              = 6           MKT_BUY_ANIMAL  = 6   # item = animal 9..11
OP_HARVEST            = 7           N_MARKET_OPS    = 7
OP_FERTILIZE          = 8
OP_DIG                = 9
OP_BUILD_COOP         = 10
OP_BUILD_PASTURE      = 11
OP_PLACE              = 12  # arg1 = item id, arg2 = n
OP_FEED               = 13
OP_CARE               = 14
OP_COLLECT_FERTILIZER = 15
OP_PICKUP             = 16  # arg1 = item id, arg2 = n
OP_DROP               = 17
N_UNIT_OPS            = 18

# ONE item id space (there is no separate crop or animal id space):
WHEAT=0 CARROT=1 TOMATO=2 STRAWBERRY=3 MELON=4 EGG=5 MILK=6 WOOL=7 FERTILIZER=8
GOOSE=9 COW=10 SHEEP=11         # crop ids == item ids 0..4; animal index = item id - 9
```

Encoding rules the recorder follows (and any encoder must):
- an op the source does not recognise, or one whose mandatory argument is missing/unknown, encodes as
  `OP_PASS` — proven equivalent, because every such case falls through `_apply_unit_action` doing
  nothing (§4.1);
- a market order that `_parse_order` rejects (`len < 3`, `n <= 0`, unknown op) encodes as `MKT_NONE`,
  which is exactly equivalent to an absent order — **but only in place**: an empty lane must keep its
  index, never be compacted away (§5.1);
- an order with a valid op but an item the op does not support (e.g. `SELL GOOSE`) is encoded
  **faithfully**, not normalised, because the engine's response (killing the order) is a behaviour the
  batched env must reproduce. The recorded corpus contains such orders.
- omitted counts are written as their effective default (`PICKUP`/`PLACE` → `1`).

Measured on the 232-episode corpus: **zero** actions required a lossy normalisation
(`unknown_unit_op = unknown_crop = unknown_item = unknown_market_op = unknown_market_item =
orders_truncated = 0`).

**No unit op takes a tile coordinate.** Every unit op acts on the tile the unit is standing on; the
contract's `y*10+x` tile encoding is unused by this game. `arg1`/`arg2` are 0 for ops that take no
argument.

### Action tensor layout

The contract writes `farmer int16 [B,3]`, `hands int16 [B,MAX_HANDS,3]`, `market int16 [B,MAX_ORDERS,3]`
but also says "actions carries both players". **A player axis is required.** WP1 uses, and WP2 must
accept:

```
farmer : int16 [B, 2, 3]
hands  : int16 [B, 2, MAX_HANDS, 3]     MAX_HANDS  = 16
market : int16 [B, 2, MAX_ORDERS, 3]    MAX_ORDERS = 10
```
Player axis index 0/1 = player id. `difftest.py` will also accept an implementation that wants
`[2, B, ...]`, but `[B, 2, ...]` is the default and is what the recorder writes.

Padding: unused hand slots = `OP_PASS`, unused market lanes = `MK_NONE`. Both are exactly equivalent to
the real simulator receiving a shorter list (§4.0 for the one exception — a `PLANT` in a slot beyond the
real hand count still counts toward the seed block, and `OP_PASS` correctly does not).

`MAX_HANDS = 16` is a **contract cap, not a game rule** — the game has no hand limit. See §16.

---

## 14. Canonical state schema (the fidelity-gate comparison surface)

`difftest.py` compares implementations through a canonical dict of tensors. **WP2 must expose it**, as
either `VecKaggriculture.canonical(state) -> dict[str, Tensor]` (preferred) or a `State` whose attributes
already carry these names. This is the one addition to the contract that WP1 needs; without it the
fidelity gate cannot run.

| key | dtype | shape | meaning |
|---|---|---|---|
| `money` | int64 | `[B,2]` | |
| `farmer` | int16 | `[B,2,2]` | `(x,y)` |
| `n_hands` | int16 | `[B,2]` | |
| `hands` | int16 | `[B,2,16,2]` | `(x,y)`, `-1` in unused slots |
| `hires_today` | int16 | `[B,2]` | |
| `n_land` | int16 | `[B,2]` | extra quadrants bought, 0..3 |
| `shed` | int32 | `[B,2,12]` | item ids 0..11 |
| `seeds` | int32 | `[B,2,5]` | crop ids 0..4 |
| `inv` | int32 | `[B,2,17,12]` | unit 0 = farmer, 1..16 = hands |
| `tiles` | int16 | `[B,2,10,10,12]` | `[...,y,x,field]`, fields below |
| `mkt_inv` | int32 | `[B,9]` | |
| `mkt_price` | int32 | `[B,9]` | |
| `shops` | int32 | `[B]` | bitmask, bit *i* = `SHOPS` order (§3) |
| `day` | int16 | `[B]` | |
| `hour` | int16 | `[B]` | |
| `step` | int32 | `[B]` | number of interpreter calls completed |

Tile field planes (last axis of `tiles`):

| idx | name | meaning / default when not applicable |
|---|---|---|
| 0 | `kind` | 0 EMPTY, 1 LOCKED, 2 WEED, 3 PLANT, 4 COOP (empty), 5 PASTURE (empty), **6 ANIMAL** |
| 1 | `crop` | crop id if PLANT else **-1** |
| 2 | `animal` | animal id 0..2 if an animal stands here else **-1** |
| 3 | `day0` | `planted_day` / `placed_day`, else **-1** |
| 4 | `flag_wf` | `watered_today` \| `fed_today`, else 0 |
| 5 | `cu` | `consecutive_unwatered` \| `consecutive_unfed`, else 0 |
| 6 | `yield_units` | else 0 |
| 7 | `mls` | `max_lifespan_step` for PLANT, else **-1** |
| 8 | `fert_until` | `fertilized_until_day` for PLANT, else **-1** |
| 9 | `cared` | `cared_today` for animals, else 0 |
| 10 | `fert_avail` | `fertilizer_available` for animals, else 0 |
| 11 | `care_bank` | `pending_care_bonus` for animals, else 0 |

An **occupied** structure is `kind = 6 (ANIMAL)` with `animal ∈ 0..2`; an **empty** structure keeps
`kind = 4/5` with `animal = -1`. `difftest.py` also accepts the alternative convention
(`kind ∈ {4,5}` + `animal >= 0`) and the item-id animal space (9..11), normalising both before
comparing — so this particular choice cannot cause a spurious failure.

**Meaningfulness masking (important).** `difftest.py` compares each tile field only where it carries
meaning, and each unit slot only where the unit exists:

| field | compared where |
|---|---|
| `kind` | always |
| `crop`, `mls`, `fert_until` | `kind == PLANT` |
| `animal`, `cared`, `fert_avail`, `care_bank` | `kind == ANIMAL` |
| `day0`, `flag_wf`, `cu`, `yield_units` | `kind ∈ {PLANT, ANIMAL}` |
| `hands[p, h]` | `h < n_hands[p]` |
| `inv[p, u]` | `u <= n_hands[p]` |

This is not a weakening: a field becomes live on exactly the step its tile/plant/animal/hand comes
into existence and is compared from that step onward, so a wrong initial value is still caught. It
only stops an implementation from failing because it leaves stale garbage in slots the game does not
read — which the real simulator also effectively does (its dicts simply lack those keys).

---

## 15. Reference vector format (`artifacts/vectors/`)

One `.npz` per episode, `ep_<nnnnn>.npz`, plus `manifest.json`. Written by
`src/gpuenv/record_vectors.py`, read by `src/gpuenv/difftest.py`.

Every file also stores `ops_fp` — a JSON fingerprint of the op-id maps and item order used to encode
its actions. `difftest.py` aborts if it disagrees with the ids currently defined by `ops.py`.

Arrays (T = 720 recorded states, A = 719 action records):
- `money [T,2] int64`, `farmer [T,2,2] int16`, `n_hands [T,2] int16`, `hands [T,2,16,2] int16`,
  `hires_today [T,2] int16`, `n_land [T,2] int16`, `shed [T,2,12] int32`, `seeds [T,2,5] int32`,
  `inv [T,2,17,12] int32`, `tiles [T,2,10,10,12] int16`, `mkt_inv [T,9] int32`,
  `mkt_price [T,9] int32`, `shops [T] int32`, `day [T] int16`, `hour [T] int16`, `step [T] int32`
  — i.e. the canonical schema of §14 with the batch axis replaced by time.
- `a_farmer [A,2,3] int16`, `a_hands [A,2,16,3] int16`, `a_market [A,2,10,3] int16`.
- scalars: `seed int64`, `agents` (2 strings), `flags` (a JSON blob of which sharp edges fired).

Index convention: `a_*[k]` is the action applied at interpreter step `k`, taking state `k` to state
`k+1`. `tiles[0]` etc. is the initial state.

---

## 15b. What has actually been verified against the running simulator

| claim | how it was checked | result |
|---|---|---|
| price curve, incl. `int(round())` half-to-even and float64 | independent reimplementation of §5.4 vs every recorded `mkt_price` | **0 mismatches / 129 600 price observations** |
| weed-spawn RNG (which tiles, which days) | batched MT19937 from §11.2 predicting live episodes, seeds 7 / 60000 / 123456789 × 29 end-of-days | **exact on every day** |
| shop-unlock RNG (which shop, which day) | same | **exact on every day** |
| `random()` / `getrandbits(k)` / `choice(n)` reproduction | 8 seeds × 32 draws; k ∈ {1,3,4,8,32}; n ∈ 1..8 after 0/5/100 prior draws | **bit-exact** |
| market index priority lane | scripted 120-melon duel, all three lane layouts | $24 317 vs $2 249 (split lanes), $13 342 each (same lane) |
| 719 interpreter calls, day 29 has no end-of-day | live episode step/day/hour trace | confirmed |
| crashed agent's final reward | agent raising at step 100 | `status=DONE, reward=3000.0`, **not** `None` |
| crash detector (§10.1) | 6 broken agents × 4 failure modes + clean control | all crashes flagged incl. step-718; 0 false positives |
| action codec is lossless | encode → decode → replay 232 episodes through the real sim | **166 808 step-states, 0 divergences** |

## 16. Surprises — read this list before implementing

1. **Market order index is a priority lane.** §5.1. Worth up to 10× on a contested product.
2. **Day 29 has no end-of-day.** §1. Nothing in unit inventories or on tiles is ever monetised there.
3. **`consecutive_unwatered` starts at 1** — an unwatered planting day kills the crop that night. §4.5.
4. **`max_held` truncates the first animal production**, unrecoverably. §8.2.
5. **`FEED` takes wheat from the unit's own inventory**, so `PICKUP` on a shed-access tile is a
   prerequisite. §4.12.
6. **`DROP` and the end-of-day auto-drop destroy overflow** (`del inv[item]` runs unconditionally);
   `PLACE` does not. §4.3, §8.5.
7. **`BUY_PRODUCT` / `BUY_ANIMAL` bypass the shed cap.** §5.2, §9.3.
8. **Hands spawn on possibly-LOCKED shed-access tiles** and are then inert until they walk off. §9.1.
9. **Standing on a LOCKED tile blocks every non-move op**, including PICKUP/DROP on `(5,4)`/`(4,5)`/`(5,5)`.
10. **`SELL` at price $1 does not add to market inventory.** §5.2.
11. **`BUY_PRODUCT` is quoted at `inventory - 1`**, so a buy/sell round trip nets exactly zero.
12. **Building COOP/PASTURE is free**; `DIG` is free; `CARE` is free; movement is free. The only money
    sinks are seeds, animals, land, hires and `BUY_PRODUCT`.
13. **An empty action list `[]` is a no-op**, identical to `PASS`.
14. **PLANT requests in hand slots that do not exist still count toward the seed block.** §4.0.
15. **`HIRE`/`BUY_LAND` consume a whole market lane** (index), so they push your SELL back a lane. §5.1.
16. **All 8 shops always unlock, by end of day 23**; only the *order* is random. §8.4.
17. **A crashed agent finishes with its money, not `None`.** §10.
18. **There is no cap on hands.** `MAX_HANDS = 16` is the contract's tensor width. In the recorded
    corpus the maximum ever observed is reported in `manifest.json` (`max_hands_seen`); if a future
    policy wants more, the contract cap must be raised, not the game changed.

---

## 17. Contradictions with `research/KNOWLEDGE.md`

`KNOWLEDGE.md` is mostly accurate about the source (the 2026-08-01 "ИСХОДНИК СИМУЛЯТОРА" section is
good). The following statements in it are **wrong or incomplete**:

1. **line 6 — "`reward=None` бывает при краше агента → трактуем как проигрыш".**
   Measured: an agent that raises at step 100 finishes the episode with `status=DONE` and
   `reward = 3000.0`, because `sim:929-931` overwrites both. **`reward is None` never survives**, not
   even for a crash on the last step (there the interpreter rewrites `status` first, so
   `core:636-637` no longer nulls the reward). ⇒ `src/arena.py:38-40`'s `-1.0` fallback and
   `src/eval_lb.py:118`'s `crash = (mu < 0 or mo < 0)` are **vacuous checks** — money can never go
   negative either (every spend is affordability-gated), so the crash counter can only ever read 0.
   Every "0 crashes" claim in the project's history measured nothing. Use §10.1.
2. **line 104 (D8) — "симулятор убивает только при cu>=2 (растение переживает один сухой день)".**
   True after the first watering, but `_new_plant` starts `consecutive_unwatered = 1`, so a crop that is
   not watered on its planting day dies that same night. The "8.26 watering per plant, 65% useless"
   analysis is therefore slightly off — the planting-day watering is never optional.
3. **line 49 / 126 — "CARE НЕ НУЖЕН" for fertilizer: correct**, and stronger than stated —
   `fertilizer_available = True` is set for every surviving animal every day *including* days it was not
   fed (as long as `consecutive_unfed < 2`).
4. **line 51/128 — "CARE даёт +1/день (не +2)" vs line 128 "множитель ×2-×4".** Both are loose. Exact:
   `CARE` on a day when the animal is *also fed* banks +1; the bank is paid out in full (subject to
   `max_held`) on the next production event, *only if the animal is fed that day*, and is zeroed
   regardless. The later description (`sim:795-799`) in KNOWLEDGE is right; the earlier "+1/день" line is
   what the code does per-day, but readers have used it to mean "+1 per production".
5. **line 120 — "АРБУЗ 120 шт → $24,317 (idx 0) против $2,250 (idx 1)".** Reproduced exactly:
   $24,317 vs $2,249, and both-at-index-0 gives $13,342 each. Confirmed, not contradicted.
6. **line 133 — sink totals ("сток арбуза = 140 шт/сезон")**: these are derived numbers, not source
   constants; they depend on the shop unlock *order* (random) because a shop unlocked on day 3 drains for
   27 days and one unlocked on day 23 for 6. Treat them as ±20 %, not exact.
7. **"Тайлы = бесплатное хранилище сверх лимита шеда 100"** (line 144): true, but note that it is only
   free until day 29 — a tile holding `yield_units` at the end is worth nothing, and a unit inventory at
   any *other* end-of-day is force-dropped into the 100-slot shed with destruction of the overflow.

---

## 18. What this spec does **not** pin down

- **`MAX_HANDS = 16` is uncomfortably tight.** The game imposes no hand limit; 16 is a contract choice.
  Across the 232-episode corpus the **maximum number of hands alive at once is 15** (`x_hyb` and the
  random-legal hire-heavy agent), i.e. one slot of headroom. A richer RL policy could legally want
  more: 16 hands in a day costs only `fib(17)-1 = $2 583`, 20 costs `$17 710`. If `MAX_HANDS` is ever
  raised, the vectors must be re-recorded (the action tensor width changes).
- **`MAX_ORDERS = 10` is exactly the game's own cap** (`maxMarketOrdersPerTurn`), so it is safe; the
  corpus shows lanes 0..9 all in use.
- **The impl's own price function is not covered when `canonical()` is absent.** `difftest.py` can
  auto-adapt a `State` that carries the game's fields under other names, but if that state has no
  `market_price`, prices are derived from `mkt_inv` with WP1's reference curve (which is itself
  verified exact, §15b) — so the comparison then tests market *inventory* and not the impl's rounding.
  Implementing `canonical()` with the impl's real prices closes this.
- **Non-default configurations.** Only the default configuration is specified. `marketParams` overrides,
  other board sizes, other `turnsPerDay` are all supported by the source and are *not* covered here.
- **Behaviour under malformed actions that raise.** `int(order[2])` / `int(action[2])` on a non-numeric
  value raises out of the interpreter and kills the episode. The integer action tensors make this
  unreachable in the GPU env, and the recorder rejects any episode whose agent emits an unencodable
  action, so the corpus never exercises it.
- **`remainingOverageTime` / timing.** Irrelevant to the GPU env; the recorder does not model it.
- **Rendering / visualiser.** Out of scope.
