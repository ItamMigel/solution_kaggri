# T045 execution fixes

No Kaggle submissions. Editable code belongs to the Codex worktree.

`build.py` reads the two exact active exports, preserves the original neural decoder,
adds default-off terminal/A1/A2 flags and produces isolated standalone variants. It
extracts only the official deterministic unit executor and transitive definitions
from installed kaggle-environments 1.32.7, avoiding a runtime engine dependency.
Exports retain the original d13 HG boundary. New wrappers raise exceptions instead
of disguising them as PASS; the gate counts BC/HG/opponent errors.

`terminal.py` simulates units in farmer/hand order with the official atomic PLANT
check and shed capacity. It preserves the market prefix through the last spending
or unknown order, increases suffix SELL quantities, and appends missing products
within ten slots. BUY fills are bounded rather than predicted using hidden opponent
orders. Positive quantities above actual stock are legal and stop at stock zero.
This is liquidation, not a claim of globally optimal final-tick trading.

A1 reserves only native FEEDs that were counted toward urgent animals. A2 separately
checks that travel/pickup/feed cost fits the remaining day. Neither fixes the HG's
broader resource reservation, overwritten non-urgent service, or day-boundary policy.

```
/workspace/solution_kaggri/.venv/bin/python lab/t045/execution/build.py
OPENBLAS_NUM_THREADS=1 /workspace/solution_kaggri/.venv/bin/python lab/t045/execution/fixtures.py
/workspace/solution_kaggri/.venv/bin/python lab/t045/execution/gate.py --out /workspace/shared/runs/t045_execution_gate32_v4 --workers 20 --variants off,a1,a2 --worlds 32 --seed-start 929454001
OPENBLAS_NUM_THREADS=1 /workspace/solution_kaggri/.venv/bin/python lab/t045/execution/report.py /workspace/shared/runs/t045_execution_gate32_v4
```

Freeze opponents before the gate; their source paths and SHA256s are in
`frozen/manifest.json`. Ozer44 and jaxa2802 came from read-only public notebook pulls;
only literal source blobs were extracted and their published hashes checked. No
notebook packaging, upload, or submission cells were run.

The gate runs both seats on fresh worlds, with BLAS=1 and at most twenty workers.
Terminal evaluation branches only the official final step; original rewards are
reproduced before each counterfactual. Full enabled-game smoke verifies equivalence.
A1 and A2 are shadow-evaluated on all 719 baseline native actions. The normalized
export code must match exactly after replacing only the constant flags. Zero action
differences certify the identical deterministic trajectory by induction; changed
trajectories use separate complete closed-loop episodes on the same worlds. The
records explicitly distinguish full games and identity certificates. Whole-world bootstrap confidence intervals are conditional on the fixed
opponent suite. Zero flips in a finite sample are not proof of global equivalence.
Large exports, frozen models, and replay logs are not committed.
