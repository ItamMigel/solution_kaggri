# BC → PPO: независимое ревью Codex — 2026-09-24

Вердикт: H100 ускорит выборки, но не исправит несоответствие log-prob, декодера и движка. До Q7 fixes запускать long PPO нельзя. При sampled BC ≈$30k против g9/Horizon ≈$150k обещать A сильнее g9 за пять дней — самообман; первый полезный результат вероятнее в reactive doubles. Один GPU всё же стоит сохранить для strongest-track.

## Q1. Факторизация действий

Для BC target-cell → работа в клетке — разумная компрессия пути. Для PPO реализация плоха: вне target направление есть deterministic argmax из logits (policy.py:120–131), а его log-prob и entropy исключены (:147). PPO не обучает направление; разные latent target часто дают одно исполненное движение. Рынок из 22 независимых bucket-ов хуже: декодер часто выбрасывает sampled bucket, но PPO всё равно оптимизирует его log-prob.

Не тратить первый день на полный autoregressive transformer. Минимальная правильная версия: target как navigation prior; затем сэмплировать допустимое направление с log-prob/entropy, либо в target — non-move op. После этого нужен sequential allocator farmer→hands для seeds/shed/inventory. Рынок лучше декодировать последовательно в 10 slots с состоянием money/shed/seeds/land/hires и STOP; временный компромисс — маскировать qty и считать likelihood только реально посланных orders.

## Q2. Compounding error

«PPO исправит сам» — нет: BC почти не проживает производственные цепочки и потому даёт мало хороших on-policy rollout.

1. Мерить effective-action accuracy после masks+decoder и долю выполненных операций, не только teacher-forced top-1. 97.1% market-key accuracy почти наверняка преимущественно zero buckets.
2. Собрать on-policy BC states; Horizon использовать отдельным recovery teacher/style, а не смешивать его labels с DSM/M&M&P&Q. Это DAgger coverage, а не top-team style.
3. State-reset curriculum (day 0/6/12/18) поможет поздним цепочкам/critic, но не заменит early-investment credit. Сейчас его нет: VecKaggriculture имеет reset(seeds), но нет loader полного State плюс MT RNG. Делать только с exact test snapshot → K actions → тот же state.

DART-noise без oracle labels не нужен: он создаёт шумные states с ложным expert action.

## Q3. Reward

Текущая награда Δown_money + 0.5·terminal_margin (ppo.py:34–35,72–73) добавляет обоим игрокам общий стимул к total money и допускает кооперативное self-play. gamma=.999, lambda=.95 даёт trace около 1/(1-.999·.95)=19 шагов; terminal margin почти не обучает d1.

Для strongest: zero-sum Δ(equity_own-equity_opp), gamma=1.0 (минимум .9999), lambda=.995–1.0 и terminal correction cash_margin - equity_margin_terminal. Equity = cash + консервативная ликвидационная стоимость shed/seeds/animals/созревшего урожая по тому же market loop, не quoted price. Correction сохраняет исходный cash-margin objective. Для doubles оставить style/BC-KL; win bonus не лечит credit. На одинаковых seeds сравнить current, zero-sum cash и potential-shaped equity; требовать value explained variance.

## Q4. Лига

Pure self-play симметричной сети недостаточен и не тестирует g9. На episode/seat: 35% frozen snapshots своей команды, 30% latest current/self, 25% doubles других команд, 10% tape/router stressors. Добавлять snapshot в pool только после fixed GPU eval с seed/hash/metrics.

Yhay 0913/0909 можно запускать GPU только после портирования action list в tensor schedule и exact transcript test official/gpuenv. Их foreign-RNG tapes already have ~38% rejected unit ops: это 10%-ный stressor, не evidence силы. Horizon/g9 остаётся periodic CPU/official gate.

## Q5. H100 параметры и логи

ENVS=1024 ставить вслепую нельзя. Только float32 board records текущего rollout требуют 1024×719×2×30×10×10×4 = 16.5 GiB; lists, stack/concat, masks и optimizer увеличат peak. Начать 256, затем 512 после замера. Для 1024 нужны fp16 board, packed masks и chunked rollout, без одновременных list+stack+concat.

Старт после fixes: 256–512 env/GPU, 2 epochs, minibatch 8192 transitions, AdamW 1e-5 trunk / 3e-5 heads, clip .10, grad-clip .5, vf .5, bf16. Entropy нормировать на число реально stochastic decisions; 1e-4 → 0. BC KL adaptive с target effective-action KL 0.01–0.03/decision; doubles сохраняют floor. Critic pretrain на replay/BC rollout returns, не fresh value head.

Нужны: old-policy approx-KL, clipfrac, ratio histogram, entropy target/move/work/market, explained variance, advantage по day, effective BC-KL, executed op distribution, rejected/no-op/blocked-plant/overflow-hire. money_mean недостаточен. Каждые 5 iters — frozen GPU league и малый official обе-seat gate; каждый returned checkpoint — fresh worlds vs g9/v5/panel, CI, crash=0, timing.

## Q6. План

A сильнее g9 за пять дней маловероятен: g9 нет в training league, а исходный BC делает примерно пятую часть cash. Не менять g9 без external paired gate. Держать 1 GPU A + 3 GPU B, не все 4 B.

Первые 24 h после fixes:

1. До отправки: reproducible smoke, decoder→gpuenv→official round-trip, LOCKED crossing, partial fills/sell-funded buys, hand cap 16/17 и exported 719-step timing. Fail = no long PPO.
2. 0–4 h: GPU0/1/2 — BC v3 DSM/M&M&P&Q/Mother-Goose; GPU3 — conditional против отдельных checkpoints. Сравнивать held-out effective behaviour и runtime, не CE. Losses не выкидывать, только clipped margin/outcome weights.
3. 4–24 h: GPU0 strongest (лучший BC + mixed frozen league), GPU1–3 — по одному double. Checkpoint /5 iters и exact configs/seeds. Если strongest не улучшает lower-CI против собственного BC base и не имеет содержательных побед в fixed external mini-gate — остановить и отдать GPU лучшему double/BC ablation.

Первый возврат: validity/value/double-vs-holdout. Второй: only official обе-seat gate vs g9/v5/panel.

## Q7. Bugs / риски до запуска

1. LOCKED movement mismatch. policy.legal_masks запрещает move в LOCKED (policy.py:70–75), но 1.32.7 разрешает crossing (gpuenv/_units.py:103–112). Та же ошибка в numpy export. E2E 0 action diffs сравнивает две одинаково неверные реализации. Исправить и добавить shed-access test.
2. Market decoder меняет политику и gradient. build_actions требует полную оплату qty (policy.py:192–199), official исполняет доступный prefix. Он не учитывает cash от ранних SELL в fixed order. Частичные и sale-funded buy исчезают, но logprob всё равно включает rejected buckets (:148). То же в bc/export.py:_market. Исправить до PPO.
3. Совместные unit actions нелегальны. Mask видит pre-step state и не резервирует ресурсы. Engine идёт по units по порядку и отменяет все PLANT crop, если total demand > seeds (gpuenv/_units.py:54–78). PLACE mask допускает product вне shed/animal вне нужной постройки. Нужен sequential allocator или reject metrics.
4. v3 из предложения сейчас не загружается. train.py фиксирует TEAMS=[mmpq,dsm,mgoose] и 6×96 (:67,97–103); CLI не поддерживает N teams/10×128. ppo.py:55 всегда создаёт default PolicyNet, поэтому иной width/depth упадёт даже с strict=False. Сохранять architecture+vocabulary checkpoint и строить из них; затем обновить export.
5. 1024-env rollout OOM. Все 719 steps обоих seats лежат в Python lists (ppo.py:24–25), затем одновременно stack/concat до del buf (:76–86). Это не streaming PPO.
6. Нет clipfrac, approx-KL, explained variance, rejected-action metrics; ratio_dev не заменяет их. Value fresh; resume не хранит optimizer/RNG. Current gamma/lambda практически отрезают long credit.
7. Hand cap. gpuenv default MAX_HANDS=16, но corpus видел 17 (gpuenv/env.py:22–26). PPO может купить лишних: simulator спишет деньги, но slot не создаст. Либо mask до 16 и то же export, либо расширить policy/state/validation до official safe max.

Дополнительно: mkt_key_acc доминируется нулями; использовать mkt_exact, non-zero precision/recall, quantity MAE и effective-order accuracy. Не выкидывать losses целиком: это survivorship bias и потеря state coverage.

