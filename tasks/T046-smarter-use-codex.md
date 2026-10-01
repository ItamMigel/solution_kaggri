# T046 — исследование Codex завершено

Отдельная headless-сессия, 2026-09-29 20:29–21:03 UTC. T045 код/процессы/gate не менялись; собственный пул сокращён с12 до4 workers по просьбе его владельца. Kaggle только read-only.

Полный русский отчёт: `/workspace/shared/research/t046_smarter_use_codex.md` — ранжирование A1–A7/B1–B8, механизм/доказательства/цена/риски, четыре H100 запуска R0/R1 и резерв R2, три варианта постобработки.

Новый сигнал: MG75/MG2-25 поверх frozen m15 s0+s1 выиграл16/16 против parent7/16 (4 worlds ×2 seats ×tetsu/yaxon). Парный score+56.25pp, bootstrapCI[18.75,87.5]; margin+$4983 CI[-987,9517].32/32DONE,0errors. Это маленький dev-screen, не promotion; дальше независимый fresh gate без подбора веса. Summary: `runs/t046_team_screen_v2/summary.json`.

Local-only entry: `/workspace/wt/codex/lab/t046/mg75_mg2/main.py` + manifest, общие исходные веса, не portable archive.

Проверки: whole-board mirror нарушен NW/land/spawn; exact own-market conditional on rival flow (SELL STRAWBERRY2 $238 vs$236); target label противоречия244→26 на2 teacher replay; bug Claude boundary-fix использует overnight reset; h23MOVE→PASS transition-equivalent, но target-accuracy не обещает gain. Исходники диагностик `lab/t046`, JSON доказательства `research/t046_*`.

Первый adapter-error run исключён. Второй64game план сокращён до первых4 worlds ДО просмотра scores по ресурсу; завершено 32 полных игры (16 парных сравнений). Вся сессия <40min, ни один pool >12workers; после21:00 arena процессов нет. Claude уведомлён через bin/say.

Official file-loader observation parity: 16/16, `research/t046_wrapper_smoke.json`; full-game loader test pending as part of independent candidate gate.
