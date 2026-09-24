# Kaggriculture war room — shared protocol for Claude + Codex

Two agents (Claude Code and Codex) work as a pair on the Kaggle **kaggriculture** simulation
competition. This directory (`/workspace/shared`) is the **shared board**: the only place where the
two of us exchange state. Read this file, then `BOARD.md`, then your inbox, at the start of every
session and before picking up work. Talk to the human in **Russian**.

## ☠ HARD RULE — NEVER SUBMIT ☠
**No agent ever submits anything to Kaggle.** Not `kaggle competitions submit`, not the Python API,
not a notebook "Submit", not via a script another agent wrote. The human submits, personally.
Kaggle is **read-only** for us: leaderboard, our submissions, episodes, replays, agent logs,
discussion topics, public notebooks, datasets. The CLI (`/workspace/shared/bin/kaggle`) and the
Python API are patched to refuse submissions — do not work around the guard, do not reinstall
`kaggle` elsewhere to bypass it. When a candidate is ready: put the frozen archive in
`/workspace/shared/candidates/<name>/` with its evidence and tell the human.

## Competition facts (as of 2026-09-23)
- Deadline **2026-09-30 23:59 UTC**. After it, active submissions keep playing ~2 weeks, then a
  single **Bradley-Terry tournament** decides the final ranking → true strength vs the field matters,
  not a lucky rating streak.
- Only the **2 most recent submissions** of a team are active on the ladder. Team "misis
  biznessmenlb" (id 16739419). Team submissions/day are limited (see `kaggle competitions submission-limits kaggriculture`).
- Medal cutoffs on public LB snapshot 2026-09-23: #1 ≈3063, #50 ≈2781, #100 ≈2719, #300 ≈2593, #500 ≈2502.
  Our horizon_v4 reached 2590 before being displaced by the two v5 uploads (ratings still settling).

## Where things are
| Path | What |
|---|---|
| `/workspace/solution_kaggri` | **Primary repo** (teammates' Horizon agents + `compare.py` harness). Branch `lab` = merged workspace. |
| `/workspace/wt/claude`, `/workspace/wt/codex` | Per-agent git worktrees (branches `lab-claude`, `lab-codex`). **Edit code only in your own worktree.** Merge into `lab` via small commits; tell the other agent in its inbox. |
| `lab/gpuenv/` | Batched torch copy of the engine (bit-exact vs the OLD engine; must be re-difftested vs kaggle-environments 1.32.7 before trusting). |
| `lab/tools/replay_mine.py`, `replay_report.py` | Re-simulate a Kaggle replay with hooks → per-episode P&L. Currently broken on engine 1.32.7 (task T001). |
| `lab/census_legacy/` | Old ladder census pipeline (download → fingerprint → taxonomy → imitation fit). |
| `lab/knowledge/` | Official rules, engine spec with undocumented mechanics, economics notes, lessons from the user's old attempt. |
| `/workspace/kaggriculture` | User's old repo (read-only reference; RL/CEM/scripted engine, opponent pool). |
| `/workspace/shared/replays/` | Downloaded Kaggle replays (large, ~30 MB each; not in git). |

Python: `/workspace/solution_kaggri/.venv/bin/python` (py3.12, kaggle-environments==1.32.7, numpy).
Torch/GPU work: `/workspace/kaggriculture/.venv/bin/python` (torch cu126, Tesla P40 24 GB).
Local game: ~14 s per game per core; box has 48 cores.

## Board layout
- `BOARD.md` — **single source of truth**: current champion, top findings, task table. Keep it short. Edit only your own rows; add rows freely.
- `tasks/T###-slug.md` — one file per task: goal, owner, hypothesis, method, **result**, next step.
- `ledger.jsonl` — append-only, one JSON per completed evaluation run (schema below). Never rewrite lines.
- `research/` — digests: Kaggle discussion threads, top-team replay analyses, engine facts. One topic per file, cite sources (topic id / episode id).
- `inbox/claude.md`, `inbox/codex.md` — messages **to** that agent. Append with `bin/say <to> "<msg>"`. The recipient marks items `[done]` when handled.
- `candidates/<name>/` — frozen agent archives ready for the human to consider submitting.
- `runs/` — logs of cross-agent headless calls.

### Ledger schema
`{"ts": "...", "by": "claude|codex", "task": "T003", "candidate": "name", "path": "...", "sha256": "...", "opponents": [...], "seeds_file": "...", "games": N, "wins": W, "draws": D, "losses": L, "mean_margin": x, "worst10_margin": x, "errors": 0, "run_dir": "...", "verdict": "better|worse|noise|n/a", "note": "..."}`

## Working rules
1. **Claim before you start**: set yourself as owner in `BOARD.md` + create the task file. Never work on a task owned by the other agent; send a message instead.
2. **CPU budget**: each agent uses **≤ 22 worker processes** at a time (48 cores; leave headroom). GPU: announce in BOARD before using it.
3. **Evidence standard** (inherited from both repos): paired seeds, both seats, diverse opponents
   (not only Horizon ancestors), whole-world CI. A claim of "better" needs a CI that excludes no-effect.
   Don't tune on `seeds/*confirmation*`. Zero crashes/timeouts is mandatory.
4. **Cross-check**: every result that would change the champion must be **independently reproduced or reviewed by the other agent** before it goes to `candidates/`. That's the point of pairing.
5. **Divide by nature of work**: prefer giving each agent different hypotheses rather than the same one. When both attack the same question on purpose (red-team), say so in the task file.
6. Write findings for the other agent to reuse: exact commands, file:line, numbers. Negative results are results — log them.
7. `/workspace` is **not persistent** (no volume). Push with `bin/sync "msg"` → branches `board` and `lab` of github.com/AdilHAA/kaggriculture (remote `mine`). Merge your worktree branch into `lab` first. Human-approved 2026-09-24: sync also mirrors to the teammates repo ItamMigel/solution_kaggri as branches `adil-board` / `adil-lab` ONLY — never push to its main or any other branch.

## Talking to each other directly (headless)
- `bin/ask_codex "<prompt>"` — runs `codex exec` in `/workspace/wt/codex`, logs to `runs/`, prints Codex's final message. Add `--bg` to run in background.
- `bin/ask_claude "<prompt>"` — runs `claude -p` in `/workspace/wt/claude`, same logging.
- `bin/say <claude|codex> "<msg>"` — async note into the other's inbox (cheap; preferred for FYIs).
Use headless calls for: independent review of a diff/result, a bounded research question, or a second opinion. Don't use them for open-ended loops.
