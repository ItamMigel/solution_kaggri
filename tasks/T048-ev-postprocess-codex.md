# T048-B — EV post-processing
Owner: Codex. Started 2026-09-30 10:00 UTC. Track A owned by Claude.
Base: /workspace/shared/candidates/t047_m26_terminal/pkg/main.py.
Authorization: headless Claude request; never submit to Kaggle. CPU workers <=6 (11.52 quota shared).
Research official market/prices/town and BC3/HG; rank EV sell veto/add, late sell schedule, market beam, value filler. Implement 1–2 default-off variants. New preregistered worlds, 16x2 h2h and 8x2 each tetsu/ozer44 with paired baseline sanity. PASS needs >=65% h2h points, 95% whole-world bootstrap margin lower >0, no sanity regression, errors/timeouts0, safe latency and independent Claude review before candidate.
Interim by13:00Z via bin/say claude; final memo research/t048_ev_postprocess_codex.md + frozen PASS archives by16:30Z.

## Frozen initial hypotheses, 10:10Z
1. sale_beam: d14+ reorder only distinct-item SELL rows after final spending/unknown order. Exact official market scorer under explicit hypothetical mirrored queue with0.5/1/1.5 quantities; original future item quantities preserved. Up to16 candidates, trust cost$0.25 per displaced row, improvement >$2.
2. late_ev: d28–29,7 non-consumable products only; observe public rival sales via market deltas minus own confirmed fill and known town demand. Empirical24-step blocks estimate short-horizon liquidation value. At most8 added/held units/item/step; native hold only immediately before known town tick with min scenario gain>=0, mean>$8 or2%; explicit next-turn release. Cash>=2000, shed free>=24 to hold. WHEAT/FERT, units and funding prefix protected.
Development probe93048201–202:12games (6unique world/opponent paths), allDONE. Development screen93048203–204:24games, not promotion evidence. Gate93048501–516 and sanity93048601–608; strict no observed points or mean-margin regression on each named sanity opponent.95%whole-world bootstrap,100000 resamples,RNG48020260930.160gate games planned. No parameter selection on gate.
Independent bounded Claude review requested via bin/ask_claude at10:11Z.

## Full gate complete, 2026-09-30 10:33Z
160/160 DONE; zero errors/timeouts/fallback counters. sale_beam formalPASS:27W/2D/3L,28/32points,mean+$157.59375,world95[+$26.84375,+$403],median+$29.15/16world margins positive,one zero. Outlier+$1944, remaining15mean+$38.5. Sanity tetsu16/16 vs16/16, delta+$3 CI[0,8];ozer44 14/16 vs14/16,delta+$7.75 CI[.375,17.875]. maxcallback.255615s,overage0.
late_ev FAIL:16/32h2h,mean0,0h2h changes;3sanity adds20units total, tetsu paired-$14.1875, ozer44 unchanged. Known oversize-hold and optimistic current-flow limitations in rejected prototype are disclosed; no archive or gate tuning.
6/6 official file-loader parity;1438/1438off action identity;min bank59.087427s.2fixed attribution games reproduce gate rewards (501 local+27/full+27;513 local+154/full+1944).206complete full games total including development andloader/reference; two initial attribution games aborted before result for BLAS import-order misconfiguration, excluded and preserved in attribution_attempt1_rejected.json.
Independent code review PASS: research/t048_ev_code_review_claude.md. Final independent result review pending before packaging. Primarylab merged fe81b8bd. Research memo updated.

## Final delivery 2026-09-30T10:40:39.787637+00:00
Independent RESULT review PASS for sale_beam. Frozen archive /workspace/shared/candidates/t048_m26_sale_beam/t048_m26_sale_beam.tar.gz;sha256 9a450bcb6d4709ff4e7d35d094690b7e6bd774994599bc47ac644b02579c9f35. No late_ev archive. Full Russian memo research/t048_ev_postprocess_codex.md. No Kaggle submissions; no active eval workers.
