# T047 — m26 post-processing
Owner: codex. Start 2026-09-30 08:49 UTC; hard stop 10:45 UTC.
Без переобучения: terminal t718; HG A1 native FEED; DSM75/MG25 weighted log-prob ensemble. По одному изменению.
Фиксированные новые миры h2h 93047001–93047016; sanity 93047101–93047108, оба места. ≤11 workers.
PASS: ≥65% points против неизменённого m26, положительный margin и нижняя граница 95% world bootstrap >0, все игры без ошибок/таймаутов. Sanity: tetsu/ozer44 по 16 игр. Никакой настройки по результатам.
Независимый review Claude требуется перед candidates по общему протоколу. Никогда не отправлять в Kaggle.

## Завершено 2026-09-30 09:09 UTC

- V1 terminal: 24/32 points (75%), mean +$190.21875, world95[+$96.8125,+$299.4375] → PASS.
- V2 A1: 16/32 points, mean0, CI[0,0] → FAIL; по одной симметрии rewards нельзя заключать, что фикс не активировался.
- V3 DSM75/MG25: 15/32 points, mean−$1922.56, CI[−$3956.29,+$64.22] → FAIL.
- 192 полные основные игры без ошибок/таймаутов. Sanity terminal tetsu16/16, ozer44 14/16.
- Добавлены32 контрольные игры неизменённого m26 на тех же sanity seeds: те же16/16 и14/16, terminal Δmargin+$176.375/+$352.0, Δpoints0/0. Все32 DONE.
- Официальный file loader:6/6 DONE, точная parity rewards, overage>=58.48s. Всего230/230 игр DONE.
- Claude независимо проверил код и пересчитал результаты: research/t047_code_review_claude.md, research/t047_result_review_claude.md.
- Frozen archive: candidates/t047_m26_terminal/t047_m26_terminal.tar.gz; SHA256 49f6b879a8d671f69bb746112247c0028b024105e26424c6ae12845835e73336. Source SHA e933f11707c6506c922b19b807cef6e4490acf430390890380d3fa4f52029839.
- Скрипты: lab/t047/{build,check,gate,sanity_control,summarize,loader_smoke,package,report}.py; commits d7f2fbe3 +4d7ee56f уже merged/pushed в lab и adil-lab.
- Terminal — небольшое улучшение последних продаж; 75% в зеркале не доказывают большой прирост рейтинга. Переобучения/отправок в Kaggle не было.
