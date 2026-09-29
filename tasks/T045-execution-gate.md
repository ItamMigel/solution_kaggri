# T045 — execution/evaluation: завершено

Codex, 2026-09-29T22:20:34+00:00. **Шесть экспериментальных архивов готовы; независимое ревью и проверка хешей пройдены. Отправок в Kaggle не было.**

Автоматически менять активную пару на этих данных не рекомендуется. t718 формально проходит гейт фиксированного пула, увеличивая margin на $156/$182, но прирост score почти полностью обусловлен собственными зеркалами. A1/A2 гейт улучшения не проходят.

| Кандидат / README | Δscore, п.п. [95% world CI] | Δmargin | Решение | Архив |
|---|---:|---:|---|---|
| [m15ens terminal](/workspace/shared/candidates/t045_m15ens_terminal/README.md) | +1.562 [+0.781, +2.539] | $+156.26 | Формальный PASS; вне зеркала score не доказан | [tar.gz](/workspace/shared/candidates/t045_m15ens_terminal/t045_m15ens_terminal.tar.gz) |
| [mix4 terminal](/workspace/shared/candidates/t045_mix4_terminal/README.md) | +1.172 [+0.391, +2.148] | $+181.78 | Формальный PASS; вне зеркала score не доказан | [tar.gz](/workspace/shared/candidates/t045_mix4_terminal/t045_mix4_terminal.tar.gz) |
| [m15ens a1](/workspace/shared/candidates/t045_m15ens_a1/README.md) | +0.000 [-1.562, +1.562] | $+50.25 | NO PROMOTION | [tar.gz](/workspace/shared/candidates/t045_m15ens_a1/t045_m15ens_a1.tar.gz) |
| [mix4 a1](/workspace/shared/candidates/t045_mix4_a1/README.md) | +0.977 [-0.195, +2.344] | $+48.21 | NO PROMOTION | [tar.gz](/workspace/shared/candidates/t045_mix4_a1/t045_mix4_a1.tar.gz) |
| [m15ens a2](/workspace/shared/candidates/t045_m15ens_a2/README.md) | +0.000 [+0.000, +0.000] | $-19.77 | NO PROMOTION | [tar.gz](/workspace/shared/candidates/t045_m15ens_a2/t045_m15ens_a2.tar.gz) |
| [mix4 a2](/workspace/shared/candidates/t045_mix4_a2/README.md) | +0.000 [+0.000, +0.000] | $+29.30 | NO PROMOTION | [tar.gz](/workspace/shared/candidates/t045_mix4_a2/t045_mix4_a2.tar.gz) |

Без собственного зеркала: m15ens t718 — 0 п.п. [0,0], 0 положительных/отрицательных изменений исхода; mix4 t718 — +0.223 п.п. [0,+0.670], один положительный флип. Все 10 положительных флипов m15ens и 6 из 7 у mix4 пришлись на собственное зеркало. Эффект нельзя переносить на пару, в которой terminal включён у обоих игроков. Нули bootstrap CI при отсутствии флипов не доказывают эквивалентность.

Гейт: 32 новых мира 929454001–929454032 × оба места × 8 frozen-соперников (tetsu, qA, ozer44/V44, yaxon5, jaxa2802, parthenos, оба текущих BC). Каждый кандидат имеет 512 парных сравнений к собственной базе. Критерий: положительная нижняя граница whole-world score CI и нижняя граница каждого семейства ≥ −3 п.п.

Фактически выполнено **1132 полных валидных игры** (1024 базовые +108 HG), **1940 точных сертификатов совпадения 719 действий** и **1024 точных terminal-ветки** последнего хода. Это 3072 парных сравнения, а не 3072 полные игры. Четыре полные HG-игры не меняют действий: два ключа mix4 в A1/A2 считались полностью из-за недоступной на тот момент базы для сертификата; rewards совпали с базой.

В принятом наборе: **0 ошибок, таймаутов и скрытых exception→PASS**, все статусы DONE/DONE, 719 вызовов, максимальный расход overage 3.06с при пороге55с. Время соперников отдельно не профилировалось. Сохранены четыре невалидные инфраструктурные попытки двух зеркальных ключей: два300s прерывания диагностированы косвенно; два600s имеют явный host_alarm_fired. Первые780 валидных результатов сохранены побайтно. Два заранее назначенных3600s повтора приняты по первым валидным исходам, без отбора по награде. Лимиты движка и байты агентов неизменны; CPU-квота контейнера11.52, основной пул10, отдельные повторы2 (исходный пул20).

Проверки: prefix/partial BUY, overflow,10 slots,719 identity-step fixtures;100 сравнений unit executor с официальным движком;5748 совпадений действий с исходными BC; четыре полных terminal игры с точным совпадением веток;16 официальных file-loader игр на финальных байтах;6 внедрённых исключений всегда пробрасываются. Граница HG d13 сохранена. A1 и A2 изолированы, комбинации не оценивались. A2 использует унаследованную модель стоимости HG.

Оба default-off wrapper-шаблона и сборщик находятся в `/workspace/wt/codex/lab/t045/execution/`; архивы включают только именованный флаг. Fail-fast риск явно раскрыт: непредвиденное исключение может проиграть весь эпизод. Универсальная монотонность cash/margin не заявляется.

Независимое [ревью результатов](/workspace/shared/runs/t045_claude_results_review.md) выполнено **до публикации**. Условие о зеркалах внесено в README/manifest/BOARD и сообщения. [Аудит архивов](/workspace/shared/runs/t045_execution_gate32_final/delivery_audit.json) подтверждает SHA256 каждого main.py и tar.gz, весь декартов набор ключей и происхождение повторов. [Summary](/workspace/shared/runs/t045_execution_gate32_final/summary.json), [сырые принятые записи gzip](/workspace/shared/runs/t045_execution_gate32_final/games.jsonl.gz), [ресурсные попытки](/workspace/shared/runs/t045_execution_gate32_final/resource_continuation.json). Все шесть результатов опубликованы в BOARD/ledger и отправлены через bin/say claude после каждого архива.

Воспроизведение: `build.py` → `fixtures.py` → `gate.py --out /workspace/shared/runs/t045_execution_gate32_final --workers 10 --wall-limit 600 --variants off,a1,a2 --worlds 32 --seed-start 929454001` → `report.py <run>` → независимое ревью → `watch_delivery.py` → `verify_delivery.py <run>`. Исторические повторы и точные хеши/пути зафиксированы в run manifest/resource_continuation; исходные JSONL сохранены gzip без потерь. Никаких Kaggle-команд отправки.

<details>
<summary>Журнал реализации и промежуточных проверок</summary>

# T045 execution/evaluation — Codex
Claimed 2026-09-29 18:42 UTC. User explicitly authorizes execution and separate candidate archives. Never submit to Kaggle.

Scope: default-off terminal t718 wrapper on frozen mix4/m15; isolated HG A1 protection and A2 reachability; no d13 change. Sources kept read-only, editable implementations only in /workspace/wt/codex/lab/t045. Up to 20 workers, BLAS=1, small summaries only.

Gate predeclaration: fresh worlds, both seats, frozen tetsu/qA, ozer44/yaxon/jaxa, parthenos and both current BCs. Whole-world paired score bootstrap, family non-inferiority lower bound -3pp; positive score CI required for recommendation. Cash alone insufficient. Zero exceptions, timeouts, swallowed PASS errors. Independent Claude review before recommending replacement. Archives may be experimental/rejected, clearly labelled.

Terminal fixtures: unchanged below t718/off, prefix slots including NOOP and BUY, 10-slot saturation, DROP overflow and unit order. HG fixtures: native urgent FEED reservation and reachable/unreachable late assignments.

## 18:51 UTC progress
Standalone fixtures PASS (100 official-unit differential cases, 719 off/early identity checks, prefix, capacity, full queue). Eight official full games PASS; 5748 action-identical calls against original exports. Exact terminal branch matches all four full enabled terminal runs. Frozen opponents include V44 public sha797d9bca309d and jaxa2802 sha944aa64c5ae1.

Predeclared full block: seeds 929452001..929452032, both bases, both seats, 8 opponents, isolated off/A1/A2 = 3072 full games. Terminal is additionally evaluated by exact official last-tick branching of the 1024 off games, reproducing the unchanged final rewards first. Results /workspace/shared/runs/t045_execution_gate32. No repeated/confirmation worlds. Copies/hashes of all opponents at lab/t045/execution/frozen.

Command: `/workspace/solution_kaggri/.venv/bin/python lab/t045/execution/gate.py --out /workspace/shared/runs/t045_execution_gate32 --workers 20 --variants off,a1,a2 --worlds 32 --seed-start 929452001`

## Evaluation efficiency amendment (19:00 UTC, no candidate changes)
Measured mix4-vs-BC wall time up to ~178s. Initial baseline-only run preserved as DIAGNOSTIC_ONLY; no score-based tuning or seed selection. Gate v2 adds exact A1/A2 shadow calls on all 719 original native actions; zero action differences certifies identical deterministic trajectory. Export normalized-source SHA256 must match after replacing only feature flags. Any changed game still runs a separate full candidate episode. Thus all 32 worlds/8 opponents/both seats are evaluated without redundant neural forwards on proven identical trajectories. Records label full_game versus exact_identity_from_baseline. Terminal remains exact last-tick branch.

## Final bytes + NEW gate block (19:04 UTC)
Official loader initially chose saved parent alias and bypassed terminal despite DONE. Fixed `del agent` before final def (197fc5d9), with dedicated regression fixture. Re-run: all 16 official file-loader games DONE, rewards EXACTLY equal callable harness for all off/terminal/A1/A2; minimum remaining overage 57.018895/60s. Optional unrelated open_spiel import warning only; no agent errors.

FINAL GATE: **32 previously unused worlds 929453001..929453032**, both seats, same 8 frozen opponents and exact rebuilt source hashes. `/workspace/shared/runs/t045_execution_gate32_v3`. Earlier gate32 and gate32_v2 are diagnostic only. Candidates unchanged algorithmically; entrypoint packaging corrected. Protocol: baseline + exact terminal branch; A1/A2 exact whole-trajectory no-op certificates or full closed-loop run if any action changes. 3072 requested records, all individually labelled.

## Independent review + duplicate SELL correction (19:24 UTC)
Claude independently reviewed code and coupling/identity method: no gate/A1/A2 blockers. Packaging P1 requires explicit disclosure that strict exceptions lose the episode rather than one PASS turn; README+manifest now disclose this, preserving task requirement of no silent PASS. Review: runs/t045_claude_execution_review.md.

Codex corrected a non-monotonicity claim from that review with exact engine fixture: two native SELL WHEAT1 orders separated by opponent BUY40, own WHEAT2, first-sale topup loses $7 cash ($10056→$10049). Evidence research/t045_terminal_nonmonotone_fixture.json. Terminal now enlarges ONLY LAST suffix SELL of each product, preserving earlier planned quantities. Added duplicate-SELL fixture; no guarantee of universal cash/margin monotonicity is claimed.

Gate v3 remains diagnostic only; no archives were delivered. FINAL v4 will use new seeds **929454001..929454032** after rerun file-loader parity. Method unchanged, all four exports included in normalized-source equality check. No candidate parameters tuned on interim results.

## v4 launched 19:29 UTC — final frozen behavior
All corrected fixtures PASS, including duplicate SELL. New 8 full off/terminal identity games PASS (5748 action identities); four official terminal branches match full enabled outcomes. All16 file-loader games match callable rewards and exact FINAL export hashes; minimum remaining overage55.458887/60s under16-worker smoke. Six fault injections rechecked.

Final command: `/workspace/solution_kaggri/.venv/bin/python lab/t045/execution/gate.py --out /workspace/shared/runs/t045_execution_gate32_v4 --workers 20 --variants off,a1,a2 --worlds 32 --seed-start 929454001`. All previous gate32/v2/v3 runs are diagnostic, excluded. Automatic per-candidate archive/README + BOARD/ledger/bin-say delivery watches v4 only.

Midpoint audit: 522/1024 baseline games valid, zero invalid records, max candidate callback0.406s and zero callback overage. A1 shadow changes30 baseline trajectories, A2 changes2. No interim performance-based decisions. Packaging additionally verifies candidate bytes against frozen gate SHA256 and full32-world/both-seat/opponent balance before any archive delivery.

## Resource continuation, same frozen candidates/worlds (20:33 UTC)
Actual cgroup CPU quota is **11.52 CPU** (`cpu.max=1152000 100000`), despite host core count. 20 workers each averaged~55% CPU. Two mix4-vs-mix4 baseline attempts on929454024 (both seats) crossed the artificial300s SIGALRM host guard (322.96/358.90s), with incomplete calls/opponent swallowed exception caught by strict audit. They are invalid, retained in v4 raw outputs, never used in score.

780 valid rows are adopted byte-for-byte into **runs/t045_execution_gate32_final**, with all weights/agent source hashes/worlds unchanged. Both failed keys and all outstanding keys are re-run at10 workers with600s host guard. Actual engine per-action timeout and overage budget are UNCHANGED. No score-dependent exclusion or parameter tuning. resource_continuation.json includes complete failed records; final package requires full32-world/both-seat/opponent balance and exact gated SHA. Gate now records explicit host_alarm_fired and opponent exception type.

Command: `python lab/t045/execution/gate.py --out /workspace/shared/runs/t045_execution_gate32_final --workers 10 --wall-limit 600 --variants off,a1,a2 --worlds 32 --seed-start 929454001`.

### Second infrastructure retry (20:45 UTC)
Other scan/canon pools competed for the11.52 CPU quota; both identical mirror keys again hit600s host SIGALRM (explicit telemetry), at623.9/633.5s. All four invalid attempts are preserved in resource_continuation.json. Main10 workers continues; a separate2-worker retry of ONLY these keys uses3600s host guard and UNCHANGED engine limits/agent bytes. No accepted outcome is discarded. Final consolidation waits until the main writer exits, archives its raw attempts, and replaces only the two invalid keys with complete valid retries. Publication remains stopped until then.

### Completion rule formalized, 20:55 UTC (before HG outcomes, after the assigned off retries finished)
Independent resource review accepts outcome-independent retries but requests a rule for any later host-alarmed A1/A2 game. Rule: **every incomplete episode with explicit host_alarm_fired==1 gets exactly one retry at3600s host guard with identical source/world/seat/opponent/engine settings; the first valid outcome is accepted regardless of reward. Any non-alarm failure or failure of that3600s retry blocks delivery.** Main600s attempts remain archived. Existing two mirror keys already have their one3600s attempt running; never repeat those again automatically. Additional retries, if any, run only after the main pool closes, with at most2workers.
The original two300s interruptions lack explicit alarm telemetry; attribution is inferred from the300s signal timer, elapsed322.96/358.90s and incomplete calls/opponent exception. The two600s interruptions have explicit host_alarm_fired=1. All remain disclosed. Timing checks cover the candidate callable; opponent timing is not independently profiled. Both main and retry set BLAS=1 in gate.py before NumPy import.

21:00 UTC: both isolated3600s mirror retries are valid (719calls, BC/HG/opponent errors0, overage0; max callback0.599/0.704s). First valid outcomes frozen in retry_games.jsonl. No additional retries of these keys authorized by the predeclared rule.

Publication ordering: finalize/consolidate → report + evaluation-only integrity audit → independent Claude RESULTS review → ONLY after PASS publish six archives with BOARD/say per candidate → archive byte audit. No candidate published yet. This enforces shared rule4 before potential champion-changing evidence enters candidates/. Intermediate26-complete-world terminal signal is +1.442pp/+1.202pp; final rule remains full32worlds, unchanged.

Independent final results review PASS (runs/t045_claude_results_review.md), with required own-mirror caveat before archive publication. Assigned off retries completed20:53:46, general retry rule formalized20:55 after them but before HG outcomes; two off retries were fixed at20:45 and accepted first valid outcomes without reward selection. Four full HG games have no action changes (two each mix4 A1/A2) because the baseline was unavailable for certificates when scheduled; disclosed explicitly.

</details>
