# T047 — m26: post-processing без переобучения

16 новых миров 93047001–93047016 × оба места против неизменённого m26; sanity: 8 других миров 93047101–93047108 × оба места против каждого tetsu/ozer44. 11 workers, BLAS=1. Порог: ≥65% h2h points, положительный mean margin и нижняя граница двустороннего 95% bootstrap CI по целым мирам >0; ноль ошибок/таймаутов.

| Вариант (одно изменение) | m26 W/D/L; points | Margin, $ [world 95% CI] | tetsu points | ozer44 points | Гейт |
|---|---:|---:|---:|---:|---|
| V1: t718 liquidation | 24/0/8; 24/32 (75.00%) | +190.22 [+96.81, +299.44] | 16/16 | 14/16 | PASS |
| V2: HG A1 native FEED | 8/16/8; 16/32 (50.00%) | +0.00 [+0.00, +0.00] | 16/16 | 14/16 | FAIL |
| V3: DSM75 / MG25 log-prob | 15/0/17; 15/32 (46.88%) | -1922.56 [-3956.29, +64.22] | 16/16 | 16/16 | FAIL |

Основной гейт: **192 игры, ошибок/таймаутов 0**. Полные симуляции официального движка, без identity/replay shortcuts. Учитывались скрытые BC/HG/terminal fallback errors и расход overage обоих игроков. Bootstrap: 100000 resamples, RNG=47020260930.

Официальный file loader: 6/6 повторов точно совпали по rewards с callable-гейтом, все DONE/DONE. Фикстуры terminal/A1, метки/веса смеси и выбор entrypoint пройдены.

Дополнительный контроль неизменённого m26 на тех же sanity-мирах: tetsu 16/16, ozer44 14/16; 32/32 без ошибок. Terminal относительно контроля: Δpoints +0/+0, Δmargin $+176.38/$+352.00 (tetsu/ozer44). Контроль добавлен после двух поражений terminal против ozer44, чтобы проверить их происхождение; варианты не менялись.

Замороженный прошедший вариант: `/workspace/shared/candidates/t047_m26_terminal`; архив `t047_m26_terminal.tar.gz`, SHA256 `49f6b879a8d671f69bb746112247c0028b024105e26424c6ae12845835e73336`.

V1 даёт небольшой денежный выигрыш в зеркале; высокая доля побед не доказывает большой прирост рейтинга против поля. A1 и смесь не рекомендованы. Вес смеси зафиксирован до старта, по этим мирам ничего не подбиралось.

Исходники/сборка: `/workspace/wt/codex/lab/t047`. Полные игры, manifest с SHA256, summary и loader parity: `/workspace/shared/runs/t047_m26_post`. Независимый review: `/workspace/shared/research/t047_code_review_claude.md` и `/workspace/shared/research/t047_result_review_claude.md`. Никаких отправок в Kaggle.
