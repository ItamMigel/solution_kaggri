# Codex chat watchdog

The host's cron calls `codex_watchdog.py` every 30 minutes. The script uses
`codex queue --thread UUID --message TEXT` to return to the same conversation;
it does not launch another headless agent or select a model. The conversation
checks the shared board, inbox, running jobs, and next authorized action.

The user paused the old T001/T003 assignment on 2026-09-23. A reminder alone
does not authorize taking those tasks. The next shared assignment controls what
work resumes. Kaggle remains strictly read-only.

The script takes a nonblocking lock and reads the local Codex queue database
in read-only mode. If **any** message is already queued for this conversation,
it skips that tick to avoid a backlog and give queued human input precedence.
A queue-schema error is logged and prevents enqueueing. This was checked with
Codex CLI 0.154.0; recheck the schema if the CLI is upgraded.

## Run and inspect

```sh
/workspace/solution_kaggri/.venv/bin/python /workspace/wt/codex/lab/tools/codex_watchdog.py --thread THREAD_UUID --dry-run
crontab -l
tail -20 /workspace/shared/runs/codex_watchdog.log
```

Installed crontab entries carry the marker `# codex-board-watchdog`. Remove that
line with `crontab -e` to stop reminders, or change its UUID when moving to a
new conversation. Preserve other cron entries when editing.

The host must be running. A queued message in a closed Codex conversation may
wait until the conversation is reopened; this script does not relaunch Codex.
The live cron entry and Codex's local conversation state are machine-local;
the code and shared setup record are pushed to Git, but do not restore a
deleted machine or conversation automatically.
