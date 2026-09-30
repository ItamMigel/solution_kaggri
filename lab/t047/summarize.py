"""Frozen whole-world bootstrap; no tuning or optional stopping."""
import json
from pathlib import Path
import numpy as np

OUT = Path('/workspace/shared/runs/t047_m26_post')


def main():
    rows = [json.loads(x) for x in (OUT/'games.jsonl').read_text().splitlines()]
    manifest = json.loads((OUT/'manifest.json').read_text())
    keys = [(r['variant'],r['opp'],r['seed'],r['seat']) for r in rows]
    expected = {tuple(j) for j in manifest['jobs']}
    assert len(keys)==len(set(keys)) and set(keys)<=expected
    result = {'records':len(rows), 'complete':set(keys)==expected,
              'errors':sum(not r['valid'] for r in rows), 'variants':{}}
    for variant in ('terminal','a1','dsm75_mg25'):
        groups = {}
        for opp in ('m26','tetsu','ozer44'):
            rr = [r for r in rows if r['variant']==variant and r['opp']==opp]
            good = [r for r in rr if r['valid']]
            seeds = sorted({r['seed'] for r in good})
            worlds = [[r for r in good if r['seed']==s] for s in seeds]
            complete = [x for x in worlds if len(x)==2 and {r['seat'] for r in x}=={0,1}]
            ci = None
            if complete:
                means = np.array([np.mean([r['margin'] for r in x]) for x in complete])
                rng = np.random.default_rng(47020260930)
                boot = means[rng.integers(len(means),size=(100000,len(means)))].mean(1)
                ci = list(map(float,np.quantile(boot,[.025,.975])))
            groups[opp] = {'n':len(rr), 'valid':len(good), 'worlds':len(complete),
                           'points':sum(r['points'] for r in good),
                           'wins':sum(r['margin']>0 for r in good),
                           'draws':sum(r['margin']==0 for r in good),
                           'losses':sum(r['margin']<0 for r in good),
                           'mean_margin':float(np.mean([r['margin'] for r in good])) if good else None,
                           'world95':ci}
        h = groups['m26']
        passed = (h['n']==h['valid']==32 and h['worlds']==16 and h['points']/32>=.65 and h['mean_margin']>0 and h['world95'][0]>0
                  and all(groups[o]['n']==groups[o]['valid']==16 and groups[o]['worlds']==8 for o in ('tetsu','ozer44')))
        result['variants'][variant] = {'opponents':groups, 'pass':bool(passed)}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
