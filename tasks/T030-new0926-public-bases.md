# T030 — new0926 public bases

Owner: codex.  Started 2026-09-26.

Goal: safely pause CMA4 at the current completed-generation boundary, recover the four remaining public notebook agents under `opponents/new0926/`, and classify their lineage before any evaluation decision.  Kaggle access is read-only; no submission.

Method: let the active CMA4 `gen_022` finish and verify `history.json`/`cma.pkl` before stopping its launcher; execute only notebook extraction/verification cells locally; download any declared Kaggle input dataset read-only; fingerprint emitted `main.py` for Horizon markers and structural origin.
