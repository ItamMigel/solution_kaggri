# Selection ledger — development evidence

No data in this file is an untouched confirmation result. Each generation was
completed to its frozen budget before selecting the next candidates.

## Generation 1: 16 worlds, 1,152 games

| Variant | Ordinary public wins / 96 | Attack wins / 32 | Interpretation |
|---|---:|---:|---|
| v4 incumbent | 86 | 0 | Severe opening vulnerability |
| Safe eight/three opening | 86 | 30 | Same ordinary win count, robust opening |
| Safe fifteen/ten opening | 86 | 2 | Cash protection alone; many small-margin losses |
| Correct final-sale attribution, eight/three | 91 | 16 | Better ordinary result; weaker attack matchup than safe8 |
| Correct attribution, fifteen/ten | 91 | 10 | No advantage over the eight/three variant |
| Correct attribution, 18-turn advance | 83 | 26 | Weaker ordinary group |
| Correct attribution, 24-turn advance | 78 | 24 | Weaker ordinary group |
| Prediction confidence filter | 87 | 4 | Weak attack matchup |
| Correct attribution plus expanded library | 92 | 20 | Worth another generation; not yet a confirmed gain |

Advance safe8 and library. New, separately declared structural mutations:
final sale-block reordering, correction confined to the replay forecaster,
and joint final-day worker assignment. Longer horizons and confidence filtering
are not advanced. Correct accounting is not automatically a stronger policy:
the legacy heuristics were tuned around the old signal.

## Generation 2: 24 new worlds, 1,440 games

Two newer public controllers were added. They share public policy ancestry;
their notebook titles are not verified ratings.

| Variant | Ordinary public wins / 192 | Attack wins / 48 |
|---|---:|---:|
| v4 incumbent | 168 | 0 |
| Safe eight/three opening | 166 | 46 |
| Correct attribution plus expanded library | 161 | 29 |
| Final sale-block reorder plus safe opening | 192 | 47 |
| Forecaster-only attribution correction | 152 | 27 |
| Joint final-day worker assignment | 166 | 44 |

All 1,440 games completed with zero callback failures. The safe opening's
ordinary result is slightly lower than v4 here; its value is the documented
cash-failure repair. Do not present its pooled attack-driven improvement as a
large ordinary-opponent gain. The new sale-block variant is the clear selection
winner on this panel. The added library's generation-one advantage did not
persist; it is rejected for this release. The more complex worker planner and
forecaster correction are also rejected.

## Generation 3: one conservative mutation, 24 new worlds

Test a single visible productive-layout similarity gate at 0.85 before applying
the extra final sale-block reorder. No threshold grid search. Compare incumbent,
safe8, queue8 and gated8 against six opponents on both seats: 1,152 games.

The declared choice is queue8 plus gated8 if the gated variant improves ordinary
score without a material subgroup or severe-loss regression; otherwise queue8
plus safe8. Then freeze both sources and all confirmation plans. This generation
remains selection evidence, even if it looks excellent.


Completed: queue8 and gated8 each won 240/240 ordinary games and 47/48 attack games. V4 won 225/240 ordinary games and 0/48 attack games. Both selected finalists therefore had zero ordinary severe losses and no ordinary subgroup regression in selection. Their exact sources are frozen for confirmation; no further tuning is allowed on that panel.
