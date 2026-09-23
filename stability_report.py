"""Descriptive tails and paired uncertainty, resampling complete world blocks.

Intervals condition on the frozen opponent suite. They do not sample new
opponent strategies, and all-success bootstrap intervals are degenerate.
"""
import argparse
import collections
import json
import math
import pathlib
import numpy as np


def interval(values):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(230923)
    draws = rng.integers(0, len(values), size=(5000, len(values)))
    means = values[draws].mean(axis=1)
    return np.quantile(means, [.025, .975]).tolist()


def wilson_lower(successes, n):
    z = 1.959963984540054
    p = successes/n
    return (p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)


def describe(rows):
    good = [r for r in rows if 'margin' in r and 'error' not in r]
    if not good:
        return dict(games=len(rows), errors=len(rows))
    blocks = collections.defaultdict(list)
    for r in good:
        blocks[r['seed']].append(r)
    sizes = {len(rr) for rr in blocks.values()}
    mm = np.array([r['margin'] for r in good])
    pp = np.array([r['points'] for r in good])
    world_points = [np.mean([r['points'] for r in rr]) for rr in blocks.values()]
    world_margin = [np.mean([r['margin'] for r in rr]) for rr in blocks.values()]
    perfect = sum(all(r['points'] == 1 for r in rr) for rr in blocks.values())
    return dict(
        games=len(rows), errors=len(rows)-len(good), worlds=len(blocks),
        games_per_world=sorted(sizes), balanced=len(sizes) == 1,
        wins=int(sum(pp == 1)), draws=int(sum(pp == .5)), losses=int(sum(pp == 0)),
        score_rate=float(pp.mean()), world_macro_score=float(np.mean(world_points)),
        world_block_score_95=interval(world_points),
        world_macro_margin=float(np.mean(world_margin)),
        world_block_margin_95=interval(world_margin),
        mean_margin=float(mm.mean()), median_margin=float(np.median(mm)),
        p10_margin=float(np.quantile(mm, .1)), worst_margin=float(mm.min()),
        worst_decile_mean_margin=float(np.sort(mm)[:max(1, math.ceil(len(mm)*.1))].mean()),
        losses_over_1000=int(sum(mm < -1000)), losses_over_5000=int(sum(mm < -5000)),
        perfect_worlds=perfect, perfect_world_fraction_wilson_lower_95=wilson_lower(perfect, len(blocks)),
        max_candidate_callback_ms=max(r['max_ms'][r['seat']] for r in good),
        non_done=sum(r.get('status') != ['DONE', 'DONE'] for r in good),
    )


def paired(rows, baseline):
    base = {(r['opponent'], r['seed'], r['seat']): r for r in rows
            if r['candidate'] == baseline and 'margin' in r}
    result = {}
    if not base:
        return result
    for name in sorted({r['candidate'] for r in rows}-{baseline}):
        rr = [r for r in rows if r['candidate'] == name and 'margin' in r]
        matched = [r for r in rr if (r['opponent'], r['seed'], r['seat']) in base]
        if not matched:
            continue
        blocks = collections.defaultdict(list)
        for r in matched:
            b = base[r['opponent'], r['seed'], r['seat']]
            blocks[r['seed']].append((r['points']-b['points'], r['margin']-b['margin']))
        means = np.array([np.mean(v, axis=0) for v in blocks.values()])
        result[name] = dict(matched_games=len(matched), unmatched_games=len(rr)-len(matched),
                            worlds=len(blocks), paired_score_gain=float(means[:, 0].mean()),
                            paired_score_gain_95=interval(means[:, 0]),
                            paired_margin_gain=float(means[:, 1].mean()),
                            paired_margin_gain_95=interval(means[:, 1]))
    return result


def report(rows, baseline='horizon'):
    keys = [(r['candidate'], r['opponent'], r['seed'], r['seat']) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate games would inflate evidence')
    result = {'candidates': {}, 'paired_against': baseline, 'paired': paired(rows, baseline),
              'pairwise': {name: paired(rows, name) for name in sorted({r['candidate'] for r in rows})},
              'limitations': ['Intervals condition on the frozen opponent suite.',
                'Both seats and all opponents in a world are resampled together.',
                'Shop-stratified summaries are post-hoc descriptive analyses.',
                'All-success bootstrap intervals are degenerate; also inspect perfect-world Wilson bounds.']}
    for name in sorted({r['candidate'] for r in rows}):
        rr = [r for r in rows if r['candidate'] == name]
        entry = describe(rr)
        entry['by_opponent'] = {opp: describe([r for r in rr if r['opponent'] == opp])
                                for opp in sorted({r['opponent'] for r in rr})}
        entry['by_seat'] = {str(seat): describe([r for r in rr if r['seat'] == seat]) for seat in [0, 1]}
        entry['by_first_shop'] = {shop: describe([r for r in rr if r.get('shops') and r['shops'][0] == shop])
                                  for shop in sorted({r['shops'][0] for r in rr if r.get('shops')})}
        entry['worst_games'] = [{k: r[k] for k in ('seed', 'opponent', 'seat', 'margin', 'shops')}
                                for r in sorted((r for r in rr if 'margin' in r), key=lambda r: r['margin'])[:12]]
        result['candidates'][name] = entry
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input'); p.add_argument('--baseline', default='horizon'); p.add_argument('--out')
    a = p.parse_args()
    result = report([json.loads(l) for l in pathlib.Path(a.input).read_text().splitlines() if l], a.baseline)
    output = json.dumps(result, indent=2)
    if a.out:
        pathlib.Path(a.out).write_text(output)
    else:
        print(output)
