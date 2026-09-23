# GPU-vectorised kaggriculture — interface contract (v1)

Frozen 2026-08-02. Three work packages are built in parallel against THIS document; anything not
specified here must be raised, not invented. Integration failure is the main risk of the whole effort.

**Backend: PyTorch, not JAX.** Verified on this box: `torch 2.11.0+cu128`, 2× RTX 5070 Ti (Blackwell,
cc 12.0), matmul confirmed working. The installed `jax 0.11.0` has **no CUDA jaxlib** and falls back to
CPU — do not build on it, and do not spend time installing a Blackwell-compatible jaxlib.

## Why this exists

Ground truth is `/venv/main/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py`
(pure Python, ~9 s per 720-step episode per core ⇒ ~2 200 steps/s across 28 cores). That throughput is the
single reason RL is currently impossible. A batched GPU reimplementation is the unlock.

**The dominant risk is not speed, it is FIDELITY.** If the fast env differs from the real one anywhere, we
train a policy for a game nobody is playing. We already have a documented instance of this failure mode:
`x_evo9` scored +102 862 on a mis-specified evaluation field and −33 333 on a correct one. Fidelity is
therefore gated by differential testing, not by inspection.

## Work packages and file ownership (do not write outside your own paths)

| WP | Owner writes | Must not touch |
|----|--------------|----------------|
| **WP1** reference spec + test vectors + difftest harness | `src/gpuenv/spec.md`, `src/gpuenv/record_vectors.py`, `src/gpuenv/difftest.py`, `artifacts/vectors/` | `src/gpuenv/env.py`, `src/rl/` |
| **WP2** batched torch env | `src/gpuenv/env.py` (+ `src/gpuenv/_*.py` submodules) | `src/gpuenv/spec.md`, `difftest.py`, `src/rl/` |
| **WP3** RL stack (obs/action design, policy, self-play, PPO) | `src/rl/**` | everything in `src/gpuenv/` |

Nobody edits: `src/eval_lb.py`, `src/animal_agent.py`, `src/rich_agent.py`, `submission/main.py`,
`artifacts/agents/**`. Those are the shipped agents and the evaluation field.

## Env API (WP2 implements, WP3 consumes, WP1 validates)

```python
# src/gpuenv/env.py
class VecKaggriculture:
    def __init__(self, n_envs: int, device: str = "cuda", dtype=torch.float32): ...
    def reset(self, seeds: torch.Tensor) -> State:      # seeds: int64 [B]
    def step(self, state: State, actions: Actions) -> tuple[State, torch.Tensor, torch.Tensor, dict]:
        # returns (next_state, reward [B] float32, done [B] bool, info)
    def observe(self, state: State, player: int) -> torch.Tensor:   # [B, OBS_DIM] float32
```

- **Batch-first**: every tensor carries a leading batch dim `B`. No Python loop over envs anywhere on the
  hot path; a loop over the 720 steps is expected and fine.
- **Two players per env.** `actions` carries both; `reward` is player 0's **final money minus player 1's**,
  emitted only on the terminal step (0.0 otherwise). Shaped/auxiliary signals belong in `info`, never in
  `reward` — WP3 decides shaping.
- **`State` is a dataclass of tensors only** (no Python objects), so it can be `torch.save`d, indexed, and
  moved between devices.

### Action tensors (fixed shape, mirrors the real action dict)

```
farmer : int16 [B, 3]                 # (op_id, arg1, arg2)
hands  : int16 [B, MAX_HANDS, 3]      # MAX_HANDS = 16; unused slots op_id = OP_PASS
market : int16 [B, MAX_ORDERS, 3]     # MAX_ORDERS = 10; unused slots op_id = OP_NONE
```

`op_id` enumeration lives in `src/gpuenv/ops.py` (WP2 authors it, WP1 must use the same file). Arguments
are pre-encoded integers: resources/crops as enum ids, quantities as raw ints.

> **CORRECTION v1.1 (2026-08-02) — my error, caught by WP3. Supersedes v1.**
> An earlier draft said arguments encode "tile targets as `y*10 + x`". **That is wrong and would have made
> this a different game.** Verified in `_apply_unit_action` (kaggriculture.py:297): a unit acts on its
> **own current tile** — the function reads `pos = _farmer_position(farm, idx)` and uses that; PLANT / WATER
> / HARVEST / CARE / FEED / PICKUP / DROP / PLACE / DIG / FERTILIZE / BUILD take **no coordinates**.
> Movement is **directional only** (`FARMER_MOVES` → `dx, dy`, one step, rejected if out of board or onto a
> `LOCKED` tile). Consequently a unit's reachable work is entirely determined by where it has walked, which
> is exactly why travel and assignment matter and why "act on an arbitrary tile" would trivialise the game.
> **No unit op may take a tile argument.** Args are for item/crop ids and quantities only.

### Both players

`actions` carries both players, batch-first: `farmer int16 [B, 2, 3]`, `hands int16 [B, 2, MAX_HANDS, 3]`,
`market int16 [B, 2, MAX_ORDERS, 3]`, where axis 1 is the player index (0/1).

### `observe()` returns raw State, not a baked feature vector

WP3 computes its own derived economics (remaining sink, projected supply, opponent-sales attribution), so
the env must expose **raw per-tile and per-unit tensors for BOTH players**, not an opaque encoding:
tile `kind`, crop/animal id, `planted_day`/`placed_day`, `watered_today`, `consecutive_unwatered`,
`yield_units`, `fertilized_until_day`, `pending_care_bonus`, `fed_today`, `cared_today`,
`consecutive_unfed`; plus money, unit positions and inventories, `hires_today`, unlocked quadrants,
shed/seed stores, market inventory and prices, and unlocked shops. A fixed opaque `observe()` vector blocks
WP3 — keep the tensors public on `State` and treat any `observe()` helper as a convenience wrapper.

`info` must include `info["money"] -> int64 [B, 2]` for league bookkeeping.

⚠️ **Market order INDEX is a priority lane** — `_process_market` iterates by order index, and the index-0
order drains the whole price curve before the opponent's index-1 order is evaluated (measured: melon 120
units → $24 307 at index 0 vs $2 250 at index 1). The batched implementation MUST preserve this ordering
semantics exactly; it is worth more than any policy improvement we have found.

## Fidelity gate (WP1 defines, WP2 must pass, non-negotiable)

1. **Trajectory equality.** For ≥200 recorded episodes spanning varied agents (starter, our crop agents,
   our animal agents, random-legal), replaying the recorded action sequences through the batched env must
   reproduce, at **every** step: both players' money, full tile state, shed/inventories, unlocked
   quadrants, hire counts, and market prices.
2. **Money equality is not sufficient** — a wrong intermediate state that happens to end on the same number
   will diverge under a different policy. Compare full state.
3. **Integer arithmetic stays integer.** Money, quantities and counts are int64/int32, never float. Prices
   follow the source's exact formula and rounding.
4. **Report the first divergence** (env index, step, field, expected vs actual), not just a pass/fail.
5. Known sharp edges that must be covered by vectors: market order index lane · `CARE` banking with the
   `max_held` cap (and that it truncates the FIRST production) · `FEED` consuming wheat from the *unit's*
   inventory (requires `PICKUP` on a shed-access tile {(4,4),(5,4),(4,5),(5,5)}) · shed cap 100 destroying
   overflow on both `DROP` and auto-drop · **day 29 has no end-of-day** (last actionable step is 718) ·
   `first_yield_day` / `LAST_PLANT` horizons · fib hire cost `fib(n+1)−1` reset daily · weed spawn RNG ·
   shop unlock schedule and town demand.

## Determinism / RNG

Same `seed` must produce the same episode as the real sim (weed spawns, shop unlock order). If exact RNG
parity proves impossible, WP1 says so explicitly and we fall back to *distributional* parity plus
seed-matched vectors for everything deterministic — but that decision is made openly, not silently.

## Performance target (secondary to fidelity)

≥1 M env-steps/s aggregate on one RTX 5070 Ti at B≈4096 (vs ~2 200 steps/s on 28 CPU cores ⇒ ~500×).
Report the honest measured number; a correct 100× is worth far more than a fast wrong env.

## Shipping constraint (WP3 keeps in view)

The submitted agent runs on Kaggle **without a GPU**: `main.py` (or tar.gz with weights at root), ~1 s/turn
budget, current agents use 0.5–2.7 ms ⇒ ~1000× headroom. A learned policy must therefore export to a
**numpy** forward pass with no torch dependency. Keep the net small enough that this is comfortable, and
keep the crash-safe wrapper — `agent` must remain the LAST module-level callable.

## Final acceptance

A trained policy is only adopted if it beats the incumbent under `src/eval_lb.py` — the **real** simulator,
17-opponent field, MIN margin, ≥3 independent seed blocks. The GPU env is a training accelerator; it is
never the arbiter.
