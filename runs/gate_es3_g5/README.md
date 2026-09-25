# Local comparison results

128 games requested on 16 world seeds; both seats. No submissions were made.

All rates below are from the candidate agent’s perspective. Confidence intervals resample whole world seeds, including both seats and all opponents. They condition on this fixed suite.

| Candidate | Opponent | W / D / L | Errors | Score rate | 95% world interval | Mean margin | Worst 10% mean | Worst margin |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| es3_g5 | es1_g9 | 32 / 0 / 0 | 0 | 100.0% | [100.0, 100.0]% | +725.0 | +44.0 | +15 |
| es3_g5 | es2_c1 | 32 / 0 / 0 | 0 | 100.0% | [100.0, 100.0]% | +704.2 | +25.0 | +9 |
| es3_g5 | v5_guarded | 28 / 0 / 4 | 0 | 87.5% | [68.8, 100.0]% | +662.8 | -286.0 | -517 |
| es3_g5 | v5_market | 28 / 0 / 4 | 0 | 87.5% | [68.8, 100.0]% | +660.9 | -286.0 | -517 |

`summary.json` includes per-seat results, severe-loss counts, worst games and paired comparisons between your candidates. A 100% observed score is not certainty. Identical policies can still have seat effects. Repeated use of a seed panel turns it into development evidence.
