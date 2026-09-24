# Local comparison results

128 games requested on 16 world seeds; both seats. No submissions were made.

All rates below are from the candidate agent’s perspective. Confidence intervals resample whole world seeds, including both seats and all opponents. They condition on this fixed suite.

| Candidate | Opponent | W / D / L | Errors | Score rate | 95% world interval | Mean margin | Worst 10% mean | Worst margin |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| es2_c1 | es1_g1 | 30 / 0 / 2 | 0 | 93.8% | [81.2, 100.0]% | +695.9 | -142.0 | -351 |
| es2_c1 | es1_g9 | 31 / 0 / 1 | 0 | 96.9% | [90.6, 100.0]% | +15.2 | -32.5 | -133 |
| es2_c1 | v5_guarded | 32 / 0 / 0 | 0 | 100.0% | [100.0, 100.0]% | +869.2 | +92.0 | +66 |
| es2_c1 | v5_market | 32 / 0 / 0 | 0 | 100.0% | [100.0, 100.0]% | +869.2 | +92.0 | +66 |

`summary.json` includes per-seat results, severe-loss counts, worst games and paired comparisons between your candidates. A 100% observed score is not certainty. Identical policies can still have seat effects. Repeated use of a seed panel turns it into development evidence.
