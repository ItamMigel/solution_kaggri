# Kaggriculture CMA-ES на CPU сервера (офлайн) — v2, 2026-09-26 вечер
**v2:** поиск идёт от es7_wm (текущий лучший): каждый кандидат = es7_wm с заменённой строкой 24 настроек (слой пшеницы и COLLECT сохраняются),
зеркало в fitness и контроль проверок = es7_wm. Прогон называется cma6 (старый cma5 не трогается). Установка/запуск — как раньше.
Эволюция 24 настроек Horizon (+ модуль COLLECT) от текущего лучшего es5_c3g15, в ОФИЦИАЛЬНОМ движке, на всех ядрах.
Агенты ничего не сабмитят — архивы для решения человека.

## Установка (без интернета; python берём от пакета BC/PPO — там уже есть numpy и kaggle-environments 1.32.7)
```bash
unzip kaggri_cma.zip && cd kaggri_cma
PY=$(cat ../kaggri_bcppo_v3/.python_path) ./scripts/setup.sh     # или PY=/полный/путь/к/python
```
Ожидается: `cma 4.5.0 | numpy … | kaggle_environments 1.32.7`, `All kit file hashes match`, `SETUP_OK`.
(Если в .python_path относительный путь — укажи полный путь к python из kaggri_bcppo_v3.)

## Запуск
```bash
./scripts/run_cma.sh          # поиск cma5 + автоматическая проверка центра каждые 5 поколений
./scripts/status.sh           # поколения (centre/best fitness) и результаты проверок GATE
```
- Ядра: min(nproc, квота cgroup) − RESERVE(24, для PBT) → 3/4 поиску, 1/4 проверкам. Пример 128: ~78 поиск, ~26 проверки.
- Параметры: POP=16 кандидатов, WORLDS=12 миров/поколение, SIGMA=0.015, GENS=80. Одно поколение ≈ 17×12×2×6 = 2448 игр.
- Fitness поколения: зеркало es5_c3g15 1/8, parthenos 2/8, metav4 2/8, 3 из {yhay0913, t2945, ozer, yaxon, pilkwang} по очереди по 1/8.
- Проверка (scripts/gate.py): центр vs es5_c3g15 на 16 НОВЫХ мирах, обе стороны, 10 соперников (es5 сам, parthenos, metav4, yhay, t2945,
  ozer, yaxon, pilkwang, es1_g9, v5_market). PASS = среднее попарное преимущество над es5 с нижней 95% границей > 0 и ни один соперник не хуже −10 п.п.
- Перезапуск после сбоя: снова `./scripts/run_cma.sh` — поиск продолжит с `runs/cma5/cma.pkl`.

## Вместе с PBT на том же сервере
PBT экзамен по умолчанию берёт ~104 воркера. Перезапусти PBT с меньшим экзаменом, чтобы CPU хватило обоим:
```bash
cd ../kaggri_bcppo_v3; pkill -f pbt_member.sh; pkill -f pbt_ctl.py; sleep 2; pkill -f "bcppo/ppo.py"; sleep 5
RESUME=1 OLD=<путь v2 runs> HORIZON=1000 ENVS=6256 MB=16384 WORKERS=16 WORLDS=6 nohup ./scripts/pbt.sh > runs/pbt_launch.log 2>&1 &
```

## Что прислать
`./scripts/status.sh` + папки `runs/gates/cma5_g*/gate.json` с PASS, и `runs/cma5/gen_XXX/c/main.py` прошедшего центра.
