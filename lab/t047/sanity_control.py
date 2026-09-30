"""Unchanged m26 controls on the already fixed sanity worlds; no retuning."""
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from gate import game, OUT


if __name__=='__main__':
    rows=[]
    jobs=[('m26',o,s,p) for s in range(93047101,93047109) for o in ('tetsu','ozer44') for p in (0,1)]
    path=OUT/'sanity_control.jsonl'
    assert not path.exists()
    with path.open('w') as f, ProcessPoolExecutor(max_workers=11) as pool:
        futures=[pool.submit(game,j) for j in jobs]
        for fut in as_completed(futures):
            r=fut.result()
            rows.append(r)
            f.write(json.dumps(r)+'\n')
            f.flush()
            print(len(rows), '/32',r['opp'],r['seed'],r['seat'],r.get('margin'),r['valid'],flush=True)
    assert len(rows)==32 and all(r['valid'] for r in rows)
