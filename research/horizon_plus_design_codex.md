# Horizon+ — review Codex (2026-09-24)

## Verdict before building

The draft has the right goal (add **small, observable, reversible** behaviours before
optimising them), but it is too optimistic about tape safety and about reusing the
final-day planner.  Do **not** start a 50-gene mixed CMA run.  First build a capability
library whose members each have a zero-effect default, a counter, and a one-module
gate.  Otherwise evolution will mostly select accidents in eight worlds.

There are two implementation facts that change the plan:

* A final `globals().update(...)` is sufficient for the 24 existing knobs because
  their functions read globals later (`lab/tools/knobs.py:36-46`).  It cannot turn
  `_SETTINGS` flags on/off: `_IMPL=make_agent(..., **_SETTINGS)` has already copied
  them into `Chassis.cfg` at `horizon_v5_market.py:963,998`, and `Chassis.__init__`
  copies settings again at :431-432.  Nor can it change literals already used to
  patch the tapes: opening wheat is assigned at :994-997, router switches are hard
  coded at :973-992, and FD takeover is `step < 696` at :7531-33.  M4 needs a real
  build-time/config wrapper, not another entry in the present `SPACE`.
* `M1` must not trust the current `_is_noop` as an engine legality oracle.  It marks
  *any* operation on `tile == "LOCKED"` as a no-op (:364), while our exact-engine
  work already found LOCKED crossing legal.  Replacing a planned move on that basis
  is an immediate positional tape desync.

## Q1 — what to build, in order

1. **M1a first: PASS-only, in-place CARE.**  Override only literal `PASS`, never a
   purported no-op; CARE does not change position or inventory.  Its sole gene is
   enable (perhaps a day window after it has a measured effect).  Record attempts,
   accepted overrides and later rejected tape actions.  Then test WATER as its own
   module; HARVEST and COLLECT_FERTILIZER as separate modules.  They are not a single
   priority permutation: harvest/collect alter carried inventory, WATER alters the
   tile, and all can change later tape validity.  FEED/FERTILIZE come last, only
   with an explicit inventory/continuation contract.
2. **Do not implement M2 as written.**  Picking fertilizer up near the shed has no
   value unless the same unit is subsequently routed to a crop; the tape normally
   owns that routing.  It also changes shed capacity, sales and later PICKUP/DROP
   validity.  First measure how often a PASSing worker already holds fertilizer on a
   fertilizable crop.  If it is near zero, the missing capability is a whole
   pickup→walk→fertilize→drop micro-plan, not a `keep_fraction` gene.  Treat that as
   a later audited macro, not an evolutionary parameter.
3. **Reject M3's proposed reuse before any search.**  `_fd_route` is explicitly a
   last-23-step liquidation heuristic: `horizon=719-step` (:7456-61), tasks compute
   crop age as `29-planted_day` (:7427-33), and it values only visible current loot
   (:7434-53).  It knows neither future production nor CARE/FEED/PICKUP/PLACE.
   `_fd_action` also replaces actions for *all* tape units (:7499-7507) and sells
   the shed (:7508-12).  Moving it to D1--D28 is not a labour module; it deletes the
   production controller.  Safe M3-lite is market-only surplus `HIRE`, followed by a
   scheduler for **new hands only**; it must prove affordability, order-slot safety,
   index stability and daily hand lifecycle first.  Do not use the FD beam until a
   mid-season, exact-state task model exists.
4. **M4 is an ablation programme, not an EA chromosome.**  `_SETTINGS` has only
   hand_align/weed_repair/sell_lead enabled in v5; budget/room/clamp/dead-stock/
   terminal/front-run are already false (:963).  Individually establish that a flag
   is non-harmful on a broad paired screen before allowing it in a genome.  Keep
   safety contracts out of the search unless their failure mode is intentional and
   measured.
5. **M5 later, and tiny.**  T017's daily 24-knob PPO gave no promotable signal, so
   multiplying those knobs by three contexts makes a low-power search worse.  After
   a module survives, allow at most one observable binary predicate and one scalar
   (e.g. clone flag → M1 enable), with fixed no-context fallback.
6. **The missing high-value capability is an audited early production macro**:
   land timing plus seed/animal mix, especially geese/strawberry/fertilizer use.
   The evidence says top agents differ from step 0, and T012 shows a market-only
   overlay firing after D5 cannot repair a D0--D3 decision.  This is not an arbitrary
   continuous gene: author 3--6 legal, bounded opening/midgame macro variants, test
   each against g9, then expose only the surviving choice to search.  Goose line is
   worthwhile only in this form; "buy goose" without a placement/feed/collection
   schedule is a cash leak.

## Q2 — tape-desync boundary

`Chassis.act` gets a deep-copied tape action then mutates it in a strict order
(:481-512).  Position alignment is necessary but insufficient: an in-place override
can change inventory, tile state, projected shed, market affordability, and what a
future tape operation means.  `hand_align` merely pads/truncates hand commands
(:518-526); it does not make a new hand productive or make a modified state match
the tape.

Safe-ish: literal PASS → CARE on the current animal; later, PASS → WATER with a
separate test.  Conditional but risky: HARVEST/COLLECT_FERTILIZER, because inventory
changes.  Unsafe until a micro-plan owns the full sequence: PICKUP, DROP, FERTILIZE,
FEED, PLACE/BUILD, any movement, and all M3 routes.  For every module add:

* run it at one named point inside the chassis ordering (not a late wrapper that
  silently bypasses budget/room/clamp layers);
* never displace a move; use exact engine application for legality, not `_is_noop`;
* reserve action/order capacity before appending market orders — `act` truncates to
  ten orders at :512 and quote ordering is meaningful;
* log `(step, actor, raw, override, legal/executed)` and gate on zero exceptions,
  zero action differences for genome zero, and a fixed-state replay audit.

New hands append after existing indices, so they need not geometrically desync the
old tape; but any all-units planner does.  This distinction is the reason to keep
M3-lite separate.

## Q3 — EA within about 800 games/generation

Current CMA consumes 832 games/generation: 13 candidates (centre + pop 12) × 8
worlds × 4 opponents × 2 seats (`knob_cma.py:25-35`).  That is barely enough for the
existing smooth 24-knob trust region; it is not enough to estimate categorical module
interactions.  The current fitness also averages raw result+margin rather than a
paired delta to g9 (`knob_es.py:24-30`).

Use a two-level procedure.

* **Capability screen (not CMA):** one enabled module/macro at a time, plus genome
  zero in every batch.  24 variants × 2 common worlds × `{g9, one rotating hard
  opponent}` × both seats = 192 games.  Keep 10 by paired delta versus zero.
* **Racing:** those 10 get 4 new common worlds × `{g9, v5, one reactive hard}` ×
  both seats = 240.  The top 4 get 8 new worlds × all five opponents × both seats =
  320.  Total 752; reserve the remainder for tie-break replication.  Rotate a real
  top-tape/imitation opponent into the hard slot rather than fitting exclusively to
  Horizon descendants.  All comparisons within a rung share worlds, opponents and
  both seats.
* **Only after a module survives** run CMA on its continuous parameters plus the
  existing 24 knobs.  Use a small categorical island/GA for masks and macro IDs;
  do not feed arbitrary integer/categorical choices to CMA as fake continuous axes.
  Inactive conditional genes must not mutate or count toward dimension.

Keep generation seed sets disjoint, hold out a locked development fold, and never
select on confirmation seeds.  Promotion remains a separately generated 16+ fresh
world, both-seat g9 head-to-head with whole-world bootstrap CI above 50%, no panel
regression, zero errors, then independent reproduction.  Report median/trimmed
margin as a guardrail; a `margin/40000` bonus must not rescue a candidate with worse
win probability.

## Q4 — PPO for gates?

Not now.  PPO cannot execute Horizon on GPU, and its existing daily-knob experiment
was a no-op/no-promotion (T017).  A CPU on-policy policy over 30 daily choices is
strictly more sample-hungry than the racing plan, while the most important decisions
are sparse, discontinuous macros.  Use evolution/bandit selection for one or two
observable module gates after their static versions work.

GPU PPO is still useful as a **proposal generator** for an exact, deployable
micro-scheduler (e.g. target/operation score for a newly hired hand), but only if the
same masked action semantics and state features are embedded in the CPU wrapper and
then passed through the Horizon gate.  It should not be used to optimise M1--M4 gates
until that transfer contract exists.

## Immediate recommendation

Claude should implement only M1a PASS→CARE with immutable default-off config and
instrumentation, plus the genome-zero action-equivalence test.  I would not take M3
or mixed-genome infrastructure next; first decide with a 192-game capability screen
whether that smallest safe module has any effect.  T020 remains independent and
continues running.
