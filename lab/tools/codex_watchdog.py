#!/usr/bin/env python3
"""Queue a periodic check-in in an existing Codex chat, without stacking reminders."""

import argparse
import fcntl
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from uuid import UUID


MESSAGE = """[codex-watchdog] Автоматическая проверка по просьбе пользователя.
Прочитай /workspace/shared/AGENTS.md, BOARD.md и inbox/codex.md.
Проверь ход уже разрешённой работы: живы ли процессы, появились ли результаты,
нет ли ошибок, блокеров или сообщений Claude, требующих следующего шага.
Если есть действующая общая задача пользователя, согласуй декомпозицию с Claude
через /workspace/shared/bin/say claude и продолжи свой разрешённый следующий шаг.
Важные результаты и блокеры фиксируй на доске, пользователю отвечай по-русски.
Последнее указание пользователя имеет приоритет: на момент настройки он попросил
НЕ брать T001/T003 и ждать новой общей задачи. Пока нового задания нет, ничего
из прежнего backlog не начинай; отсутствие задачи не является застоем.
Не запускай дубли уже работающих процессов и не меняй чужие задачи.
Код правь только в /workspace/wt/codex. Kaggle только для чтения: НИКОГДА не submit.
При отсутствии изменений достаточно короткого статуса; не создавай новые
расписания, не переустанавливай этот cron и не пиши Claude повторные пустые пинги.
"""


def log(message):
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {message}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thread", required=True, type=UUID)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    thread = str(args.thread)
    codex_dir = Path(os.environ.get("CODEX_HOME", "/root/.codex"))
    runs = Path("/workspace/shared/runs")
    runs.mkdir(parents=True, exist_ok=True)
    with (runs / f"codex_watchdog_{thread}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            log("skip: another watchdog invocation is running")
            return 0
        # Read-only access; codex queue is the sole writer of Codex queue state.
        # Defer to any pending message, including a human's, and fail closed if
        # a future Codex version changes this schema.
        with sqlite3.connect((codex_dir / "queue_1.sqlite").as_uri() + "?mode=ro", uri=True) as db:
            pending = db.execute(
                "SELECT COUNT(*) FROM queued_items WHERE thread_id = ?", (thread,)
            ).fetchone()[0]
        if pending:
            log(f"skip: thread {thread} already has {pending} queued message(s)")
            return 0
        command = [
            "/root/.local/bin/codex", "queue", "--thread", thread,
            "--message", MESSAGE,
        ]
        if args.dry_run:
            log(f"dry-run: would queue check-in for {thread}")
            return 0
        result = subprocess.run(
            command, cwd="/workspace/wt/codex", capture_output=True,
            text=True, timeout=30, check=True,
        )
        log(f"queued for {thread}: {result.stdout.strip()}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, sqlite3.Error, subprocess.SubprocessError) as error:
        log(f"ERROR: {error}")
        sys.exit(1)
