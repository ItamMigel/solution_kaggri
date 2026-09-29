# HG — herd guard for the BC agents (2026-09-29)
`hg_layer.py` is appended to a BC agent main.py (it re-binds `agent`, so it stays the last callable).
Engine facts it relies on: an animal leaves its structure after two consecutive unfed days; FEED needs WHEAT in the unit
inventory; PICKUP only from the four shed-adjacent tiles (4,4),(5,4),(4,5),(5,5); units act before the market.
Build: `cat candidates/bc3_mix4_mg_v2/main.py lab/pavel/hg/hg_layer.py > main.py`.
Evidence: runs/compare/bc_league32b (live, 32 worlds x 2 seats, 16 opponents), runs/replay_eval/bchg_*.jsonl.
