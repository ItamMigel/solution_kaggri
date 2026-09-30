# T047 — m26, три независимых изменения

Никакого обучения или Kaggle submit. Исходный m26 копируется побайтно.

- `terminal`: ровно T045 t718 liquidation, только последний рыночный ход.
- `a1`: native urgent FEED резервирует своего работника в HG.
- `dsm75_mg25`: тот же ансамбль весов, weighted log-prob смесь DSM 75% / MG 25%; четыре члена, веса .375/.375/.125/.125. Новые члены разделяют веса с родителями, отдельны только one-hot tv.

Python: `/workspace/solution_kaggri/.venv/bin/python`.

```bash
python lab/t047/build.py
python lab/t047/check.py
python lab/t047/gate.py --workers 11
python lab/t047/summarize.py
python lab/t047/loader_smoke.py
```

`loader_smoke.py` запускать после завершения основного пула. Артефакты: `/workspace/shared/runs/t047_m26_post/`. Полные 192 игры: 16 новых миров × 2 места против m26 и 8 других новых миров × 2 места против каждого tetsu/ozer44, каждый вариант. Никаких identity shortcuts. Всего 100000 world bootstrap resamples, двусторонний percentile 95% CI. PASS требует >=65% h2h points, положительный mean margin и нижнюю границу CI>0, полный объём/0 ошибок во всех трёх матчапах. Проверки учитывают скрытые BC/HG/terminal fallback errors и временной бюджет обоих игроков.

Код сохраняет исходные fallback. Terminal при исключении возвращает действие родителя. Любое такое исключение дисквалифицирует локальный гейт.
