# Kaggriculture data generator + world/value models (offline) — 2026-09-26
Goal: a strong LEARNED world model (conditional flow matching over day-level farm state) and value model (expected final margin)
trained on many games of OUR agents (es7_wm, es6, es5, es3, top-RE) and the public pool, for Monte-Carlo planning.
Agents never submit to Kaggle.
## Install (no internet): same python as kaggri_cma (numpy + kaggle-environments 1.32.7); training needs torch (kaggri_bcppo_v3 venv).
```bash
unzip kaggri_datagen.zip && cd kaggri_datagen
PY=/full/path/to/python ./scripts/setup.sh
```
## Run
```bash
RESERVE=24 GAMES=20000 ./scripts/run_gen.sh      # CPU league games → runs/shards (~80 KB/game, ~1.6 GB per 20k games)
tail -f runs/gen.log                              # "worker done, games so far N"
# any time later (can run while generation continues):
TPY=/path/to/torch/python GPU=0 ./scripts/train_gpu.sh   # → runs/models.json, runs/train.log
```
Matchups: 45% es7_wm vs pool/older, 10% es7 mirror, 15% top-RE vs es7/es6/pool, 10% es3/5/6 vs pool, 20% pool vs pool.
Send back: runs/train.log and runs/models.json (and `du -sh runs/shards; ls runs/shards | wc -l`).
