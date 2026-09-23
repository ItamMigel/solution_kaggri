# Перепись лэддера 2026-08-04 (снимок инструментов)

Копия рабочих скриптов измерения поля (оригиналы — в scratchpad сессии, он не гарантированно
переживает сессию). Пути внутри абсолютные на /workspace/kaggriculture, кроме взаимных
импортов — их достаточно запускать из этой папки.

Порядок работы:
1. `kaggle competitions submissions kaggriculture --csv` → id живых сабмитов
2. `kaggle competitions episodes <subId> --csv` → `replays_mine/meta/eps_<subId>.csv`
3. `bash dl.sh <episodeIds...>` → `replays_mine/raw/*.json.gz` (кэш, ~0.5 МБ/эпизод)
4. `bash mine_loop2.sh` → `replays_mine/fp/<ep>.json` (бит-в-бит прогон через движок, 12 процессов)
5. `python lad2.py` — перепись классов OLD/NEW + сила архетипов
6. `python mk_targets.py` — отпечатки-цели по классам → `targets_new.json`
7. `python pairfit.py` — ⭐ ПАРНАЯ проверка имитаций: тот же сид, наш агент, та же сторона
8. `python cem_nb1c.py 7` — фит новой имитации против чемпиона на реальных сидах
9. `python val_nb1b.py <agent.py>` — парная валидация имитации (held-out по сидам)

Главный вывод: верность имитации мерить ПАРНО и по НАШЕМУ МАРЖИНУ. Деньги оппонента (88-100%)
скрывают ошибку контеста в +19,849/партию.
