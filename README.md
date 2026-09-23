# Kaggriculture — comparison kit for our teammate

Compare your agent against the submitted Horizon versions before choosing the
team's next candidates. **This kit only runs local matches. It cannot upload
or select submissions, and no Kaggle account or credentials are needed.**

## Submitted v5 solutions — 24 September 2026

Both exact archives passed Kaggle validation (**COMPLETE**):

| Candidate | Standalone source | Archive | Kaggle submission |
|---|---|---|---|
| **Market — preferred locally** | [horizon_v5_market.py](agents/horizon_v5_market.py) | [horizon_v5_market.tar.gz](submissions/horizon_v5_market.tar.gz) | **56504560** |
| Guarded — alternative | [horizon_v5_guarded.py](agents/horizon_v5_guarded.py) | [horizon_v5_guarded.tar.gz](submissions/horizon_v5_guarded.tar.gz) | **56504572** |

The uploads were explicitly authorized. Further submissions require a new
request; this comparison code still cannot upload anything. Their initial 600
ratings are starting values, not evidence of leaderboard strength. Hashes and
receipts are under [results/round4](results/round4/v5_submission_summary.json).

Both preserve v4's production and twelve-turn sale anticipation. They protect
opening cash for hires and reapply sale ordering after the final action is built.
Guarded requires at least 85% visible productive-layout similarity for that extra
pass; it was not stronger than Market on our panel.

On 64 fresh worlds against six reacting public controllers, both seats, Market
won **767/768**, Guarded **764/768**, and saved v4 **726/768**. On a separate
64-world direct panel, each new candidate won **126/128** against saved v4.
The full selection and confirmation effort completed 6,784 games on 232 distinct
worlds with zero callback failures. The opponents share substantial ancestry;
this does not establish superiority to verified top-player agents.

Read the [v5 validation report](docs/v5_validation_report.md),
[research notes](docs/v5_research_notes.md), and
[selection ledger](docs/v5_selection_ledger.md). Original v3/v4 files and the
historical comparison ZIP are preserved.

After the setup below, compare your agent against the latest three choices:

```sh
.venv/bin/python compare.py --agent friend=../my_agent/main.py --baselines v4_12turn v5_market v5_guarded --seeds-file seeds/v5_smoke.json --workers 2 --out runs/v5_smoke
.venv/bin/python compare.py --agent friend=../my_agent/main.py --baselines v4_12turn v5_market v5_guarded --seeds-file seeds/v5_development.json --workers 4 --out runs/v5_development
```

These new pools were not used to tune the agents. Freeze a candidate before
using `seeds/v5_confirmation.json`. The existing default comparison remains
v3, eight-turn v4 and twelve-turn v4; select the v5 aliases explicitly.

## Historical v3/v4 comparison

| Code | Role | Historical public-panel result |
|---|---|---:|
| `agents/horizon_v3.py` | Keep as the reference | 496/512 wins |
| `agents/horizon_v4_8turn.py` | Eight-turn sale anticipation | 490/512 wins |
| `agents/horizon_v4.py` | Twelve-turn sale anticipation | 482/512 wins |

V4 is not an established general upgrade. The twelve-turn agent beat v3 in
252/256 direct games, but had worse cash margins and lower-tail results on the
broader public panel. Paired win-rate differences on that panel remain uncertain.
Matchups matter; please do not compare only against the newest version.
See [the completed 2,496-game audit](docs/stability_report.md).

Each agent is a standalone Python file with no external assets or third-party
runtime dependencies. Matching `main.py` archives are in `submissions/` for your
team to review. Those are agent artifacts, not this comparison kit ZIP.
The agents are Apache-2.0 derivatives; preserve LICENSE and NOTICE.md.

## Setup — Python 3.12

Unzip the kit, enter this directory, then create a clean environment:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps kaggle-environments==1.32.7
.venv/bin/python compare.py --verify-only
```

On Windows, use `py -3.12 -m venv .venv` and replace `.venv/bin/python` with
`.venv\Scripts\python.exe`. Only dependencies needed by Kaggriculture are installed;
the official package lists many optional dependencies for unrelated games. Add
your own agent's dependencies to this environment if needed. No GPU is required
by our agents. A clean environment avoids importing unrelated heavyweight games.

## Run a small smoke check first

Place your standalone `main.py` somewhere accessible (or pass its folder).
Relative asset/helper imports must work with Kaggle's own source loader.
Each game starts in your candidate's folder, so relative model paths resolve
there. Additional opponents with external assets should resolve their own paths;
both agents share that working directory inside the official runner. Our three
baselines have no external assets. Kaggle's source loader does not provide
`__file__`; use a supported entrypoint/asset layout and test it before a long run.

```sh
.venv/bin/python compare.py --agent friend=../my_agent/main.py --seeds-file seeds/smoke.json --workers 2 --out runs/smoke
```

This plays **12 games**: two worlds × three Horizon opponents × both seats.
Your normal one-argument or two-argument Kaggle entrypoint is supported by the
official loader. Keep that entrypoint as the last callable defined in the file;
adding a helper afterward can change what Kaggle executes.

## Compare one or two candidates

```sh
# Development: 32 fresh worlds, 192 games per candidate.
.venv/bin/python compare.py --agent friend=../my_agent/main.py --seeds-file seeds/development.json --workers 4 --out runs/development

# Compare two alternatives on exactly the same worlds and opponents.
.venv/bin/python compare.py --agent friend_A=../candidate_a/main.py --agent friend_B=../candidate_b/main.py --seeds-file seeds/development.json --workers 4 --out runs/two_candidates

# After choosing and freezing a candidate: 128 other worlds, 768 games.
.venv/bin/python compare.py --agent finalist=../finalist/main.py --seeds-file seeds/confirmation.json --workers 4 --out runs/confirmation
```

Read `runs/.../README.md` and `summary.json`. You get W/D/L by opponent, both seats,
whole-world bootstrap intervals, cash margins, worst-10% outcomes, severe losses,
callback timing, failures and paired comparisons between your candidate versions.
`games.jsonl` contains every result. `manifest.json` freezes paths, hashes, seeds,
versions and the planned game count. Existing result directories are never
overwritten. Any game error or changed input invalidates the run and exits with
code 2; do not quietly discard failures or count them as wins.

Every game uses the official `make(...).run(...)` runner in a **fresh subprocess**,
so imported helper-module state cannot leak from one game to another. This is
slower than the internal fast interpreter loop used in some research audits.
The default wall-clock limit is 180 seconds per game; increase `--game-timeout`
for expensive imports/models if necessary. Normal official action/overage limits
still apply. Python and NumPy RNGs are seeded reproducibly; seed Torch/JAX inside
your policy if you require deterministic comparisons.

Add non-Python dependencies or weights to the hash checks with repeated
`--asset ../my_agent/model.bin` arguments. Input Python files are hashed
automatically; dependencies not supplied as assets are not fully fingerprinted.

## Add diversity and inspect failures

The three Horizon variants share ancestry. Beating them does not establish broad
strength. Include independently designed, reacting opponents:

```sh
.venv/bin/python compare.py --agent friend=../my_agent/main.py --opponent independent=../another_agent/main.py --seeds-file seeds/development.json --out runs/diverse

# Rerun a specific failed world and keep official replay JSONs (large files).
.venv/bin/python compare.py --agent friend=../my_agent/main.py --baselines v3 --seeds 12345 --workers 1 --save-replays --out runs/debug_world

# Directly compare your two agents; the v3 reference is retained as well.
.venv/bin/python compare.py --agent friend_A=../candidate_a/main.py --baselines v3 --opponent friend_B=../candidate_b/main.py --seeds-file seeds/development.json --out runs/direct
```

`--save-replays` can write 20–35 MB per game, so use it for targeted diagnostics.
Agents execute local Python code: use your own code or trusted sources.

Use common seeds within a comparison and new seeds between confirmation rounds.
The provided smoke, development and confirmation pools are disjoint and were
not used to tune the shipped agents. Once inspected or used for selection,
confirmation becomes development evidence. Do not keep selecting configurations
against it. Identical hidden seeds can produce different later shops when farm
occupancy changes; no shop schedules are overridden here. Two seats are correlated,
which is why uncertainty is calculated by world rather than by individual game.
Freeze the decision criteria before confirmation too: `--decision-note "..."`
records them in the run manifest. Do not stop a run early because its current
result looks favorable.

## Suggested handoff back to the team

Share the selected agent file/archive plus the run's `manifest.json`,
`summary.json`, `games.jsonl`, and a short description of weak matchups.
Prioritize win rate while checking bad losses and runtime. The current user
instruction prohibits further submissions until explicitly requested.
