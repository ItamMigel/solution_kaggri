# Codex watchdog — 2026-09-23

Пользователь отменил немедленный старт T001/T003: ждём новую общую задачу,
после неё декомпозируем работу с Claude. Эти задачи не начинались.

Пользователь выбрал период **30 минут**. Установлен root crontab:

```cron
*/30 * * * * /workspace/solution_kaggri/.venv/bin/python /workspace/wt/codex/lab/tools/codex_watchdog.py --thread 01a0d09a-d741-73f0-9587-c336d6bb4d4c >> /workspace/shared/runs/codex_watchdog.log 2>&1 # codex-board-watchdog
```

Текущий thread: `01a0d09a-d741-73f0-9587-c336d6bb4d4c`.
Код: `/workspace/wt/codex/lab/tools/codex_watchdog.py` (`lab-codex`, далее `lab`).
Инструкция: `lab/tools/codex_watchdog.md`.

Проверка: dry-run прошёл; реальный `codex queue` принял напоминание;
повторный запуск пропустил уже существующее сообщение. Это проверяет постановку
в очередь; доставка происходит при обработке очереди текущим чатом.

Скрипт читает очередь Codex без записи, не копит сообщения и не запускает
параллельного агента. Напоминание требует проверять shared AGENTS/BOARD/inbox,
ход разрешённых процессов и следующий шаг; оно не снимает паузу пользователя.
Kaggle — только чтение, никаких submit.

Отключить: удалить только строку с `# codex-board-watchdog` через `crontab -e`.
Лог: `/workspace/shared/runs/codex_watchdog.log`.
Машина должна работать; закрытый чат может обработать очередь только при
повторном открытии. Cron и локальная история чата не восстанавливаются из Git
автоматически после потери машины.
