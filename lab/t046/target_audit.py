"""Audit target-label/monotone-decoder compatibility on cached factual expert replays."""
import gzip
import json
from collections import Counter
from pathlib import Path

MOVES = {'NORTH': (0,-1), 'SOUTH': (0,1), 'EAST': (1,0), 'WEST': (-1,0)}
ROOT = Path('/workspace/shared/research/t045_replays')


def audit(path, player):
    d = json.load(gzip.open(path,'rt'))
    rows = {}
    for t in range(len(d['steps'])-1):
        farm = d['steps'][t][0]['observation']['farms'][player]
        a = d['steps'][t+1][player]['action'] or {}
        acts = [a.get('farmer') or ['PASS']] + list(a.get('hands') or [])
        for i,pos in enumerate([farm['farmer']]+farm['hands']):
            rows[t,i] = (tuple(pos), acts[i][0] if i<len(acts) and acts[i] else 'PASS')
    counts = Counter(); examples = []
    for (t,i),(pos,op) in rows.items():
        counts['unit_rows'] += 1
        if op not in MOVES:
            continue
        counts['moves'] += 1
        tt=t
        while (tt+1,i) in rows and (tt+1)//24==t//24:
            tt+=1
            if rows[tt,i][1] not in MOVES:
                break
        target,last_op = rows[tt,i]
        corrected = target
        if last_op in MOVES:
            dx,dy=MOVES[last_op]
            corrected=(min(9,max(0,target[0]+dx)),min(9,max(0,target[1]+dy)))
            counts['boundary_chain_moves'] += 1
        dx,dy=MOVES[op]
        actual=(min(9,max(0,pos[0]+dx)),min(9,max(0,pos[1]+dy)))
        # An out-of-board move no-ops, so this is recorded separately.
        if actual == pos:
            counts['wall_moves'] += 1
            continue
        def compatible(tgt):
            return ((dx>0 and tgt[0]>pos[0]) or (dx<0 and tgt[0]<pos[0]) or
                    (dy>0 and tgt[1]>pos[1]) or (dy<0 and tgt[1]<pos[1]))
        old_bad=not compatible(target); new_bad=not compatible(corrected)
        counts['old_incompatible'] += old_bad
        counts['fixed_incompatible'] += new_bad
        counts['targets_changed'] += target!=corrected
        if old_bad and t%24!=23:
            counts['old_bad_not_h23'] += 1
        if new_bad and len(examples)<5:
            examples.append(dict(step=t,unit=i,position=pos,op=op,old=target,fixed=corrected))
    return dict(path=str(path),team=d['info']['TeamNames'][player],seat=player,counts=dict(counts),remaining_examples=examples)


def main():
    out=[audit(ROOT/'episode-115344920-replay.json.gz',0),audit(ROOT/'episode-115343521-replay.json.gz',0)]
    Path('/workspace/shared/research/t046_target_audit.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out))


if __name__ == '__main__':
    main()
