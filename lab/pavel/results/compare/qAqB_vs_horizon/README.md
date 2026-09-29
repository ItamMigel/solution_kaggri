# Local comparison results

768 games requested on 64 world seeds; both seats. No submissions were made.

All rates below are from the candidate agent’s perspective. Confidence intervals resample whole world seeds, including both seats and all opponents. They condition on this fixed suite.

| Candidate | Opponent | W / D / L | Errors | Score rate | 95% world interval | Mean margin | Worst 10% mean | Worst margin |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| qA | v4_12turn | 111 / 0 / 17 | 0 | 86.7% | [78.1, 94.5]% | +856.5 | -579.8 | -981 |
| qA | v5_guarded | 102 / 0 / 26 | 0 | 79.7% | [69.5, 89.1]% | +630.9 | -823.7 | -1187 |
| qA | v5_market | 104 / 0 / 24 | 0 | 81.2% | [71.1, 89.8]% | +633.0 | -823.7 | -1187 |
| qB | v4_12turn | 107 / 0 / 21 | 0 | 83.6% | [74.2, 92.2]% | +805.7 | -734.5 | -1463 |
| qB | v5_guarded | 102 / 0 / 26 | 0 | 79.7% | [69.5, 89.1]% | +581.8 | -969.5 | -1461 |
| qB | v5_market | 102 / 0 / 26 | 0 | 79.7% | [69.5, 89.1]% | +584.1 | -969.5 | -1461 |

`summary.json` includes per-seat results, severe-loss counts, worst games and paired comparisons between your candidates. A 100% observed score is not certainty. Identical policies can still have seat effects. Repeated use of a seed panel turns it into development evidence.
