# Non-RL discussion digest — T004

Read through the read-only Kaggle CLI on 2026-09-24. These are decision rules
for Horizon experiments, not evidence that a particular control change works.

| Source | Finding | Concrete use here |
|---|---|---|
| [#742856](https://www.kaggle.com/competitions/kaggriculture/discussion/742856), “What actually predicted the ladder” | A passive or frozen opponent creates a different market. The author found local margin correlations close to zero until using strong trading opponents and ladder-derived seeds. They also report that near the top many wins are separated by under $1k; paired win rate and per-opponent results were more informative than aggregate bank. | T012 must retain M&M&P&Q tapes as diagnostics but use v5/v4, Parthenos and Tschinkel as decisive opponents. Report paired both seats, win rate and per-opponent breakdown; do not select a production overlay from cash alone. |
| [#742856](https://www.kaggle.com/competitions/kaggriculture/discussion/742856) | Fixed seed + fixed agents reproduce ladder outcomes under 1.32.7. The post also warns that agents silently returning PASS can look like a low-bank result instead of a crash. | Keep the full-state gpuenv parity gate and make a starting-money bank a failure signal. The T012 overlay needs replay attribution of completed PLANT/FERTILIZE actions and final unused inputs before its score is interpreted. |
| [#734000](https://www.kaggle.com/competitions/kaggriculture/discussion/734000), “How path dependent…” | Reports very different transient ratings for byte-identical submissions; commenters describe early matchmaking and seed effects. | Do not recommend replacing either active v5 submission from a short rating swing. Use local paired evidence; the human, not agents, decides any submission. |
| [#731215](https://www.kaggle.com/competitions/kaggriculture/discussion/731215), Daily Top Episodes Dataset | Daily index prioritizes high average-rating games but has a fixed 20GB/day cap; replay count is affected by file size. | Use it for candidate replay discovery and macro statistics, then re-simulate selected episodes. Do not treat its raw episode distribution as an unbiased policy-training set. |

## Immediate tests

1. For every market-only T012 overlay, replay at least one firing game and
   record successful `PLANT STRAWBERRY`, `FERTILIZE`, final seed/fertilizer
   stock, and callback time. Inputs without matching unit work are a loss,
   not an intervention.
2. Gate only a passing, attributed overlay on the diverse paired suite. A
   tape-only improvement is insufficient because tapes are brittle on foreign
   seeds.
3. Keep the two current ladder agents until a broad local comparison supports
   a replacement and the human chooses to submit it.
