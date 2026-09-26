# Kaggriculture BC→PPO v3 (4×H100) — T027, Claude + Codex
## Что нового по сравнению с v2.1
- **Исправления по аудиту Codex:** P0 — рынок сэмплируется последовательно с потолком по оставшимся слотам (записанное действие == исполненное,
  log-prob/KL честные); P1 — энтропия только по реально возможным ключам; P2 — ранняя остановка PPO по target-KL (0.015).
- **Скорость:** соперники из лиги считаются только на своих играх (раньше каждый — на всём батче); векторизованный распределитель юнитов.
- **Масштаб:** по умолчанию 2048 игр/GPU, minibatch 65536, 1 эпоха, lr 5e-6, clip .12, λ .99 (память ≈ 25–40 ГБ/GPU вместо 10).
- **Телеметрия:** approx_kl_max, early_stopped, blocked_plant, hire_overflow, выпущенные ордера.
- **Данные:** 13 топ-команд + **es3** (774 партии нашего лучшего агента es3_g5) + **es3dart** (2000 партий es3_g5 с шумом исполнения ε=.05–.3 и
  чистыми метками — лечит провал чистого BC-двойника: без DART он давал 0/96).
- Проверено здесь: greedy e2e numpy↔GPU 0 расхождений; тест потолков рынка; все 4 линии `run_all_v3.sh` отработали (tiny-режим).
## Требования
Как в v2 (+ wheel kaggle-environments лежит в корне: `pip install --no-deps kaggle_environments-1.32.7-py3-none-any.whl`).
RAM: BC на всех данных держит ~15–20 ГБ на процесс.
## Запуск (нужны чекпойнты прошлого прогона v2 на сервере)
```bash
unzip kaggri_bcppo_v3.zip && cd kaggri_bcppo_v3
USE_SYSTEM_PYTHON=1 PYBIN=$(cat ../kaggri_bcppo_v2/.python_path) ./scripts/setup.sh   # или обычный setup.sh
NVIDIA_TF32_OVERRIDE=0 ./scripts/check.sh                                            # 3 проверки
OLD=/путь/к/kaggri_bcppo_v2/runs ./scripts/run_all_v3.sh                             # все 4 GPU в фоне
./scripts/status.sh
```
| GPU | этап 1 | этап 2 |
|---|---|---|
| 0 | BC mix (13 команд + es3 + DART, 10×128) → экзамен | PPO `strong_mix` (стиль es3, KL-пол .01) |
| 1 | — | PPO `v3_cont` от лучшего strong_v3 (it319 или last) |
| 2 | — | PPO `v3_fresh` от bc_v3_all с настройками v3 |
| 3 | BC Horizon-двойник (es3 + DART, 8×128) → экзамен | PPO `double_es3` (KL-пол .05 — держит стиль Horizon) |
Экзамены и автооценка — в официальном движке против es3_g5 (наш лучший), es1_g9, v5, клона yhay и parthenos, 8 миров.
Если OOM — `ENVS=1024 OLD=... ./scripts/run_all_v3.sh`.

## PBT = эволюция поверх PPO (все 4 H100 на сильнейшую линию)

Популяция из 4 агентов (по одному на GPU) стартует с ОДНОГО сильного чекпойнта. Каждый раунд (K=10 итераций PPO)
агенты учатся в общей лиге (друг против друга + замороженные BC-двойники команд), затем CPU-контроллер экзаменует
всех в ОФИЦИАЛЬНОМ движке против es3_g5 / es1_g9 / v5_market на общих мирах, вместе со стартовым чекпойнтом как
контролем (fitness = результат − контроль на тех же мирах). Худший берёт веса лучшего + мутированный геном:
lr, ent, clip, epochs, kl_floor, target_kl, **team** (стиль-«учитель»: dsm/mgoose/mmpq/decem/vadim) и **opps**
(против каких командных двойников учиться). Лучший чекпойнт — `runs/pbt/best/` (+ архив для ЧЕЛОВЕКА; агенты не сабмитят).

```bash
# остановить старые прогоны (strong_mix/double_es3 мертвы; v3_cont/v3_fresh — после выбора START)
pkill -f ppo_rounds.sh; pkill -f "bcppo/ppo.py"; pkill -f auto_eval.sh
OLD=/путь/к/kaggri_bcppo_v2/runs START=runs/v3_cont/itNNN.pt HORIZON=1000 ENVS=6256 MB=16384 ./scripts/pbt.sh
./scripts/pbt_status.sh          # состояние агентов, экзамены по поколениям, лучший
tail -f runs/pbt/ctl.log         # экзамены / EXPLOIT
```
- CPU определяется сам: min(nproc, квота cgroup) → воркеры экзамена = CPU − 4×OMP − 8 (128 → ~104), 12 миров.
  Если экзамен не успевает за раундом (~37 мин) — `WORLDS=8` или `K=15`.
- `HORIZON` — общий PPO/KL-горизонт в итерациях; агент останавливается на нём (1000 ≈ 2+ суток).
- Перезапуск после сбоя: `RESUME=1 OLD=... ./scripts/pbt.sh` (START не нужен).
- Проверено на P40 (2 агента, 8 игр): раунд → экзамен + контроль → EXPLOIT → следующий раунд.

Это development-селекция: `runs/pbt/best/` перед решением человека перепроверяем на отдельных мирах.
## Что прислать
Вывод `./scripts/status.sh` и строки экзаменов/оценок:
```bash
for f in runs/eval/*/arena_*/README.md; do echo "== $(basename $(dirname $(dirname $f)))"; grep -E "^\| " "$f" | grep -E "es3_g5|es1_g9|v5_market|yhay0913|parthenos" | cut -d'|' -f3,4,8; done
```
