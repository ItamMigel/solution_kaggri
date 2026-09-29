# T045 — независимый аудит Pavel BC3 + HG
Owner: codex. Started 2026-09-29.

Scope: review Claude draft first; audit Pavel code/notes/results and prior BC/PPO/gpuenv; public research read-only; rank 1–2 execution tracks before 2026-09-30 23:59 UTC.
Constraints: no Kaggle submissions, no long jobs; any small experiment <=16 workers and <=15 minutes; code edits only Codex worktree.
Deliverable: /workspace/shared/research/t045_bc_improve_codex.md, notify Claude via bin/say.

## Result (2026-09-29)

Completed. Independent review is in `research/t045_bc_improve_codex.md`: retain current 2-model m15+HG d13 as baseline; only fresh-data controlled fine-tune is worth a remaining training slot, and only with an untouched holdout plus export parity/timing and paired fresh gate. PPO, search, new HG/ensemble and terminal hybrid are rejected for the deadline.
