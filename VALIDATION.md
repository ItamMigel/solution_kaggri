# Compatibility verification — 23 September 2026

Tested in a clean Python 3.12 environment using only the documented minimal
dependencies and official kaggle-environments 1.32.7.

- Ten normal games completed with 719 callbacks per agent, including all three
  frozen Horizon sources, one-argument entrypoints, and relative asset loading.
- Four intentionally crashing games were rejected: two first-turn exceptions
  and two final-turn exceptions. Final-turn crashes were detected even though
  the official final statuses were DONE and both agents had 719 callbacks.
- Two forced wall-timeout attempts were rejected. Failed runs retained their
  logs, produced reports marked invalid, and exited with code 2.
- Official replay JSON export was checked for all four export fixtures.
- Every archive contains exactly main.py with bytes matching its source file.
- After extraction to a different directory, integrity checks and two official
  games passed; paired cash margins matched the original run exactly.

These are compatibility regression checks on two reused smoke worlds, not new
strength evidence. The 32 development and 128 confirmation worlds were unused
by these checks. See [machine-readable checks](results/kit_validation.json) and
[the historical strength audit](docs/stability_report.md).

No Kaggle login, API credentials, uploads, submissions, or selection changes
were used. The ZIP excludes test fixtures, local runs, credentials, and replays.

## V5 addition — 24 September 2026

The original checks above apply to the preserved v3/v4 kit. The two new v5
archives contain `main.py`, `LICENSE.txt`, and `NOTICE.txt`, with `main.py` exactly
matching each standalone source. Both passed Kaggle validation (56504560 and
56504572). Eight official archive-loader checks and four extracted-kit games
passed locally, in addition to the recorded strength evaluations. See
[the v5 report](docs/v5_validation_report.md) and
[archive checks](results/round4/official_validation.json).
