# T024 — Ladder losses of es1_g1 and es1_g9

**Snapshot.** Read-only download from the Kaggle episode API began 2026-09-25 and captured every completed episode returned then: **121 `es1_g1`** (last captured end 01:29 UTC) and **66 `es1_g9`** (last captured end 01:31 UTC). The ladder remains live, so this is a reproducible snapshot, not a claim about later matches. Fingerprints are in `research/census_ours/fp/`; detailed re-simulated reports for all losses below −$1k are in `runs/t024_replay_reports.txt`.

**Method.** `census.py mine --workers 4` re-simulated all 187 files with kaggle-environments 1.32.7. `replay_report.py` was then run on every 27 loss below −$1k. A real g1 win, episode 112889566, encodes a timeout as `"action": null`; `replay_mine` now normalizes that to `{}` (commit `d6f3ba4`) and this replay re-simulates to its recorded $144,828/$19,832 outcome.

Kaggle replay metadata supplies team names but no opponent submission id, source or rank. Therefore “Horizon descendant” cannot be identified honestly from these files. The only reproducible family proxy below is **same terminal macro**: exact equality of final `animals` and bought `seeds` dictionaries. It is descriptive, not ancestry.

## Outcomes and repeat opponents

### es1_g1

- **121 games, W–D–L 73–0–48, mean margin $+4,490, median $+169.**
- 23 losses below −$1k: 1 same-terminal-macro and 22 different-terminal-macro.

| opponent | games | our W–D–L | mean margin | note |
|---|---:|---:|---:|---|
| Rojiomote | 3 | 2–0–1 | $-51 | mixed |
| kuro0315 | 3 | 2–0–1 | $+517 | mixed |
| Matt Motoki | 3 | 0–0–3 | $-8,035 | repeated loss |
| Julia Chien | 2 | 2–0–0 | $+58,098 | no loss |
| Ryoya Tsuruoka | 2 | 1–0–1 | $-240 | mixed |
| codezzzsleep | 2 | 1–0–1 | $+1,600 | mixed |
| OxFFFs | 2 | 1–0–1 | $-713 | mixed |
| Omar Althobaiti | 2 | 1–0–1 | $-203 | mixed |
| Ghost Rule | 2 | 1–0–1 | $+576 | mixed |
| Pilea55 | 2 | 2–0–0 | $+1,290 | no loss |
| Erfan Eshratifar | 2 | 0–0–2 | $-5,192 | repeated loss |
| trantrikien239 | 2 | 0–0–2 | $-836 | repeated loss |
| arutyunoff | 2 | 0–0–2 | $-7,816 | repeated loss |
| asteriam | 2 | 2–0–0 | $+1,188 | no loss |
| beeyan | 2 | 1–0–1 | $-150 | mixed |
| qianqiuwushang | 2 | 1–0–1 | $+16 | mixed |
| Joseph Adamski | 2 | 0–0–2 | $-12,061 | repeated loss |
| rhythm master | 2 | 1–0–1 | $-899 | mixed |
| Matin Urdu | 2 | 0–0–2 | $-2,152 | repeated loss |
| fshindo | 2 | 2–0–0 | $+216 | no loss |
| Tariq Alyami | 2 | 2–0–0 | $+276 | no loss |
| Ishan Karnick | 2 | 1–0–1 | $+35 | mixed |

### es1_g9

- **66 games, W–D–L 55–0–11, mean margin $+6,676, median $+1,278.**
- 4 losses below −$1k: 0 same-terminal-macro and 4 different-terminal-macro.

| opponent | games | our W–D–L | mean margin | note |
|---|---:|---:|---:|---|
| Koba | 2 | 0–0–2 | $-11,166 | repeated loss |
| yukino | 2 | 2–0–0 | $+947 | no loss |

The repeatable field signals are **Matt Motoki: 3–0 against g1, mean −$8,035**, **Joseph Adamski: 2–0, −$12,061**, **Koba: 2–0 against g9, −$11,166**, and smaller repeat losses to Erfan Eshratifar, arutyunoff and Matin Urdu. No large-loss cluster is an exact terminal mirror: the lone g1 same-terminal-macro loss is Civitasmass (−$1,317).

## Every loss below −$1k

`worst day/gap` is the largest intraday-end money deficit of us relative to the opponent. It shows when the loss is visible, not a causal intervention point.

| sub | episode | opponent | final margin | terminal herd ours / theirs | total hires ours / theirs | second land ours / theirs | worst day/gap |
|---|---:|---|---:|---|---:|---|---:|

| es1_g1 | 112966445 | AI是我的豆包 | $-20,308 | 8/6/3 / 11/3/3 | 261 / 282 | d6:NE,d11:SW / d6:NE,d9:SW | d29 / $-20,308 |
| es1_g1 | 113090464 | Matt Motoki | $-14,051 | 8/6/3 / 8/3/2 | 279 / 272 | d6:NE,d11:SW,d18:SE / d6:NE,d9:SW | d27 / $-15,835 |
| es1_g1 | 112930708 | arutyunoff | $-12,709 | 8/6/3 / 10/3/8 | 262 / 287 | d6:NE,d11:SW / d6:NE,d9:SW | d29 / $-12,709 |
| es1_g1 | 112982470 | Joseph Adamski | $-12,092 | 8/6/3 / 8/5/4 | 263 / 262 | d6:NE,d11:SW / d7:NE,d10:SW | d29 / $-12,092 |
| es1_g1 | 112954195 | Joseph Adamski | $-12,030 | 9/5/3 / 8/5/5 | 262 / 261 | d6:NE,d11:SW / d7:NE,d10:SW | d29 / $-12,030 |
| es1_g1 | 112929510 | Erfan Eshratifar | $-8,527 | 6/6/5 / 6/4/7 | 282 / 292 | d6:NE,d11:SW,d18:SE / d6:NE,d11:SW,d18:SE | d28 / $-9,542 |
| es1_g1 | 112920157 | Ryo Hasegawa | $-8,373 | 9/5/3 / 9/7/6 | 265 / 283 | d6:NE,d11:SW / d6:NE,d10:SW | d29 / $-8,373 |
| es1_g1 | 113084650 | Matt Motoki | $-6,267 | 8/6/3 / 8/3/2 | 261 / 286 | d6:NE,d11:SW / d6:NE,d9:SW | d29 / $-6,267 |
| es1_g1 | 113088169 | Matt Motoki | $-3,788 | 6/6/5 / 5/3/5 | 262 / 278 | d6:NE,d11:SW / d6:NE,d9:SW | d27 / $-4,561 |
| es1_g1 | 112940112 | arutyunoff | $-2,922 | 6/11/0 / 10/11/4 | 276 / 294 | d6:NE,d11:SW / d6:NE,d9:SW | d29 / $-2,922 |
| es1_g1 | 112917828 | Justin Yang | $-2,727 | 6/11/0 / 6/11/0 | 289 / 293 | d6:NE,d11:SW,d18:SE / d6:NE,d11:SW,d18:SE | d28 / $-3,078 |
| es1_g1 | 112918971 | Ghost Rule | $-2,722 | 9/5/3 / 10/4/3 | 260 / 278 | d6:NE,d11:SW / d6:NE,d11:SW | d29 / $-2,722 |
| es1_g1 | 112961824 | Matin Urdu | $-2,632 | 6/4/7 / 4/4/9 | 270 / 268 | d6:NE,d11:SW / d6:NE,d11:SW | d25 / $-3,114 |
| es1_g1 | 112933069 | OxFFFs | $-2,267 | 6/6/5 / 6/6/5 | 262 / 266 | d6:NE,d11:SW / d6:NE,d11:SW | d29 / $-2,267 |
| es1_g1 | 113019240 | rhythm master | $-2,134 | 8/9/0 / 8/9/0 | 281 / 282 | d6:NE,d11:SW,d18:SE / d6:NE,d11:SW,d18:SE | d26 / $-3,264 |
| es1_g1 | 112992603 | forever young | $-1,873 | 9/5/3 / 9/5/3 | 263 / 274 | d6:NE,d11:SW / d6:NE,d11:SW | d28 / $-1,880 |
| es1_g1 | 112939059 | Erfan Eshratifar | $-1,858 | 6/17/0 / 6/17/0 | 298 / 307 | d6:NE,d11:SW,d12:SE / d6:NE,d11:SW,d12:SE | d28 / $-2,090 |
| es1_g1 | 113007196 | Matin Urdu | $-1,673 | 8/9/0 / 8/9/0 | 263 / 281 | d6:NE,d11:SW / d6:NE,d11:SW,d18:SE | d29 / $-1,673 |
| es1_g1 | 113026868 | Yaojinming | $-1,544 | 8/6/3 / 8/6/3 | 263 / 266 | d6:NE,d11:SW / d6:NE,d11:SW | d29 / $-1,544 |
| es1_g1 | 112923665 | Civitasmass | $-1,317 | 6/11/0 / 6/11/0 | 277 / 281 | d6:NE,d11:SW / d6:NE,d11:SW | d29 / $-1,317 |
| es1_g1 | 113064117 | Syed Asad Ali | $-1,210 | 6/11/0 / 6/11/0 | 279 / 282 | d6:NE,d11:SW / d6:NE,d11:SW | d28 / $-1,331 |
| es1_g1 | 112911919 | Ryoya Tsuruoka | $-1,173 | 6/17/0 / 6/17/0 | 296 / 300 | d6:NE,d11:SW,d12:SE / d6:NE,d11:SW,d12:SE | d26 / $-1,720 |
| es1_g1 | 112979396 | yomogii | $-1,032 | 8/6/3 / 8/6/3 | 263 / 270 | d6:NE,d11:SW / d6:NE,d11:SW | d26 / $-1,483 |
| es1_g9 | 113065629 | Koba | $-16,943 | 12/5/0 / 14/3/0 | 263 / 284 | d6:NE,d11:SW / d6:NE,d8:SW | d22 / $-20,671 |
| es1_g9 | 113043248 | Koba | $-5,390 | 6/6/5 / 5/3/0 | 262 / 275 | d6:NE,d11:SW / d6:NE,d8:SW | d20 / $-9,461 |
| es1_g9 | 113091607 | MKGA | $-3,897 | 9/5/3 / 9/5/3 | 263 / 266 | d6:NE,d11:SW / d6:NE,d11:SW | d25 / $-4,729 |
| es1_g9 | 113072058 | subsubsubagent | $-1,685 | 6/11/0 / 8/9/0 | 278 / 267 | d6:NE,d11:SW / d6:NE,d11:SW | d26 / $-2,326 |

## Where the money gap opens

Across g1’s 23 large losses, our money is still **+$3.2k at day 12** and **+$2.7k at day 15** on average; it turns **−$1.5k at day 24**, **−$3.5k at day 27**, and finishes **−$5.4k**. For g9’s four large losses, the analogous path is **+$1.5k at day 12**, **−$4.6k at day 18**, **−$8.2k at day 27**, final **−$7.0k**. This excludes an opening-only explanation and points to later production/market composition.

For g1 large losses, opponents grossed $49.9k more revenue but also spent $44.5k more; they hired 9.0 more worker-days on average (only $1.0k more hire cost). The dominant gross-revenue difference is wheat (+$41.4k, +1,060 sold units), followed by tomato (+$3.7k) and carrot (+$2.5k). That is **not** a tape-safe target: the wheat gain is matched by purchase spending and represents a different commodity plan.

For g9’s four large losses, the direction reverses: we grossed $27.5k more and spent $34.5k more. Opponents gained mostly strawberry (+$8.1k) and milk (+$4.8k) while we over-committed wheat (−$33.8k opponent-minus-us revenue). Again this is a macro allocation/cash-flow effect, not an omitted local operation.

### Repeated and high-margin cases

- **Koba vs g9**, episodes 113043248 (−$5,390) and 113065629 (−$16,943): Koba takes SW on day 8 in both, versus our day 11. In the latter match, Koba sells $66.6k strawberry and $38.6k milk; ours is $43.6k and $29.5k. Our lead at day 15 (+$5.3k) becomes −$10.0k by day 18 and −$16.8k by day 21. In 113043248 we sell 3,635 wheat for $143k but spend $158k total, while Koba sells only 471 wheat, spends $20.8k and still finishes ahead. This is direct evidence against blindly adding more wheat throughput.
- **Matt Motoki vs g1**, episodes 113084650/113088169/113090464 (−$6,267/−$3,788/−$14,051): Matt takes SW on day 9 each time, versus our day 11. Their late mix uses fewer melons (54 vs our 72) and much less fertilizer selling (185–205 vs our 328–341), with more carrot and tomato revenue. In 113090464 our day-18 third-land purchase and extra hiring raise total cost to $36.0k vs $25.6k while their tomato revenue is $35.8k vs $18.9k; our deficit grows from −$1.4k d18 to −$15.8k d27.
- **Joseph Adamski vs g1**, 112954195/112982470 (−$12,030/−$12,092): they spend roughly $144–156k to make $234–268k, largely 3.3–3.7k wheat sales, and finish only $12k ahead. We lead through day 21 in both. This is a high-turnover alternative macro, not a missing action in an otherwise shared tape.
- **MKGA vs g9**, 113091607 (−$3,897): final herd and crop mix are nearly the same, and the money deficit already exists at day 12 (−$1.8k). MKGA has +32 milk and +23 fertilizer sales. It is the closest case to a same-macro efficiency problem, but only one observation and no replay-visible safe unit action identifies a causal residual.

## Actionability ranking

| rank | observation | action class | recommendation |
|---:|---|---|---|
| 1 | Earlier SW land (d8–9 vs our d11) repeats in both Koba and all Matt losses, with late strawberry/carrot/tomato advantage. | New conditional macro / build-time knob; it changes market queue and all downstream routing. | Keep as a **conditional** hypothesis only. The existing unconditional land-early change is already closed (−0.42), so do not rerun it unchanged. Any test needs a predeclared route/price condition and a fresh paired panel. |
| 2 | Opponents carry +6.5 to +9 worker-days in large losses, while the cash gap opens after d18. | New scheduling macro. | Not tape-safe: hiring changes worker indices/tape timing. M3-lite already failed; no appended-hand rerun from this aggregate signal. |
| 3 | g1’s gross wheat difference and g9’s wheat overcommitment are opposite signs. | Market/production macro. | Reject a global wheat knob or tape-safe sell/buy patch; aggregate direction is regime-dependent and costs offset revenue. |
| 4 | `COLLECT_FERTILIZER` is the only established local safe improvement (es2_c1). WATER/FEED/CARE residual screen was inert or negative (T023). | Tape-safe module. | **No new tape-safe candidate from T024.** The losses require land, commodity mix and worker scheduling, which a safe appended no-movement operation cannot repair. |

**Decision.** T024 produces no capability screen. Starting `race.py` without a causal tape-safe intervention would be tuning a macro hypothesis against a tiny, changing ladder slice. Preserve es2_c1 as the current local module; if CMA or a future macro search supplies a route-conditioned land/commodity proposal, gate it against es2_c1 on fresh worlds in both seats.

## Reproduction

```bash
# read-only Kaggle download used explicit submission ids 56522075 (g1), 56532237 (g9)
/workspace/solution_kaggri/.venv/bin/python lab/tools/census.py mine \
  --index /workspace/shared/replays/ours/index.jsonl \
  --out /workspace/shared/research/census_ours --workers 4
/workspace/solution_kaggri/.venv/bin/python lab/tools/replay_report.py \
  /workspace/shared/replays/ours/episode-<id>-replay.json.gz
```

