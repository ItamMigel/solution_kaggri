# T048-B: EV post-processing

Base: frozen `/workspace/shared/candidates/t047_m26_terminal/pkg/main.py`.
No weights, features, base controller or herd guard are modified. Never submit.

`postprocess.py` defaults to `mode='off'` and returns the original action object.
`build.py` appends the wrapper to the exact base source, embeds the official
market function dependency closure, and exports explicit off/sale_beam/late_ev
files. Exceptions return the base action and are counted; the gate rejects any
counter increment, including inherited BC/HG/terminal fallbacks.

- `sale_beam`: from step336, considers permutations of distinct-item SELL rows
  after the final spending/unknown order. Quantities, slots, all unit actions and
  the spending prefix stay fixed. Official per-unit lockstep scoring uses three
  hypothetical rival queues; these are assumptions, not observed rival orders.
- `late_ev`: from step672 through717, seven non-consumable products only.
  Public inventory changes and own known sells identify rival flow away from the
  price floor. Recent24-step flow blocks plus exact next town consumption value
  a <=4-step wait. At most8 units/item are appended or postponed. Holds only last
  one turn, preserve the native slot with NOOP when necessary, and are explicitly
  released. WHEAT/FERTILIZER trades are never modified.

```bash
/workspace/solution_kaggri/.venv/bin/python lab/t048/build.py
/workspace/solution_kaggri/.venv/bin/python lab/t048/check.py
/workspace/solution_kaggri/.venv/bin/python lab/t048/gate.py \
  --stage gate --workers 6 --out /workspace/shared/runs/t048_ev_gate
/workspace/solution_kaggri/.venv/bin/python lab/t048/summarize.py
```

Gate: each variant16 new worlds×both seats against base;8 other worlds×both seats
against each of tetsu/ozer44, with unchanged-base paired controls.160 full games.
PASS requires >=65% h2h points, two-sided95% whole-world margin CI lower>0, and
no observed points or mean-margin regression on either sanity opponent. All
errors/timeouts must be zero. A finite sanity panel cannot prove non-inferiority.

Development: probe93048201–202; screen93048203–204. Gate93048501–516;
sanity93048601–608. Bootstrap100000 resamples,RNG48020260930. No parameter
tuning on gate worlds. Candidate packaging also requires independent Claude
review and official file-loader parity. Reproduction should use a new output
directory or the exact original manifests; never overwrite frozen evidence.
