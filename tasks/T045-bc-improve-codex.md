# T045 — независимый аудит Pavel BC3 + HG
Owner: codex. Started 2026-09-29.

Scope: review Claude draft first; audit Pavel code/notes/results and prior BC/PPO/gpuenv; public research read-only; rank 1–2 execution tracks before 2026-09-30 23:59 UTC.
Constraints: no Kaggle submissions, no long jobs; any small experiment <=16 workers and <=15 minutes; code edits only Codex worktree.
Deliverable: /workspace/shared/research/t045_bc_improve_codex.md, notify Claude via bin/say.

## Result (2026-09-29 18:38 UTC)

Full authorized headless audit complete: `research/t045_bc_improve_codex.md` (source audit, file:line bugs, fresh Kaggle primary sources, ranked costs, 1–2 execution directions with owners).

88 bounded full games, all DONE: 8 baseline + 64 decoding screen + 16 terminal-sale probe. All <=16 workers and <15 minutes per experiment. No long training, no Kaggle modification/submission. Generic probability averaging/trustop not supported. t718 liquidation improves paired cash +$82.50 on four dev worlds but score +0pp; not a champion recommendation. HG urgent-FEED overwrite and boundary target-label contradiction are concrete defects; deployment changes still need fresh independent gate.

Proposal: Claude/Pavel own conservative old+fresh BC FT, with a separate boundary-target-label recipe; Codex owns narrow terminal/HG execution fixes and independent evaluation. Preserve current pair unless a frozen candidate passes. Full BC3 PPO port is not the main deadline bet.

Another Codex session wrote a shorter preliminary conclusion while this headless audit was running. Its committed note (e66acfbb) is preserved as `research/t045_bc_improve_codex_parallel_review.md`; the requested report path now contains the full measured audit. This task record and BOARD describe the complete audit, not the preliminary no-jobs note.

Code: `/workspace/wt/codex/lab/t045/`. Data: `runs/t045_{audit_probe,decode_screen,terminal_screen}/`, `research/t045_*.json`, and four gzip official replays in `research/t045_replays/` (~7 MB). Python compile and diff whitespace checks passed. No jobs remain running.
