"""Publish each completed frozen candidate and its honest gate result to Claude."""
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
RUN=Path('/workspace/shared/runs/t045_execution_gate32_final')
SHARED=Path('/workspace/shared')


def main():
    review=json.loads((HERE/'review_status.json').read_text())
    assert review.get('performance_review_passed'), 'independent results review required before publication'
    status=RUN/'delivered.json'
    delivered=set(json.loads(status.read_text()) if status.exists() else [])
    while len(delivered)<6:
        rows=[]
        for line in (RUN/'games.jsonl').read_text().splitlines():
            try:rows.append(json.loads(line))
            except json.JSONDecodeError:pass
        if any(not r['valid'] for r in rows):
            raise RuntimeError('gate contains invalid episode; no automatic candidate delivery')
        counts=Counter((r['base'],r['variant']) for r in rows)
        for variant in ('terminal','a1','a2'):
            compare='off' if variant=='terminal' else variant
            if any(counts[b,compare]!=512 for b in ('m15ens','mix4')):continue
            if all(f't045_{b}_{variant}' in delivered for b in ('m15ens','mix4')):continue
            env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
            subprocess.run([sys.executable,str(HERE/'report.py'),str(RUN)],check=True,capture_output=True,text=True,env=env)
            subprocess.run([sys.executable,str(HERE/'package.py'),'--run',str(RUN),'--variant',variant],check=True,capture_output=True,text=True,env=env)
            summary=json.loads((RUN/'summary.json').read_text())
            for base in ('m15ens','mix4'):
                name=f't045_{base}_{variant}'
                if name in delivered:continue
                e=summary['results'][f'{base}_{variant}'];out=SHARED/'candidates'/name
                manifest=json.loads((out/'manifest.json').read_text())
                ci=e['delta_score_ci95'];verdict='local gate PASS; independently reviewed' if e['recommendation_gate'] else 'NO PROMOTION'
                message=(f"T045 candidate {name}: 32 NEW worlds x8 frozen opponents x2 seats, 512 paired evaluations. "
                         f"W/D/L {e['wins']}/{e['draws']}/{e['losses']}; delta score {100*e['delta_score']:+.3f}pp "
                         f"CI[{100*ci[0]:+.3f},{100*ci[1]:+.3f}], margin {e['delta_margin']:+.2f}; {verdict}. "
                         f"Zero gate errors/timeouts. README+archive: {out}. Independent results review completed; human decision. No Kaggle submission.")
                stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
                # Only append a Codex finding; do not rewrite the other owner's task rows.
                with (SHARED/'BOARD.md').open('a') as f:
                    f.write(f"\n- {stamp} — **{name}**: Δscore {100*e['delta_score']:+.3f}pp "
                            f"(world CI {100*ci[0]:+.3f}…{100*ci[1]:+.3f}), Δmargin ${e['delta_margin']:+.2f}; "
                            f"512 paired evaluations /32 new worlds, zero errors; **{verdict}**. `candidates/{name}/README.md`. [codex]\n")
                selected=[r for r in rows if r['base']==base and r['variant']==compare]
                margins=[]
                for r in selected:
                    rew=r['terminal']['rewards'] if variant=='terminal' else r['rewards'];p=r['seat'];margins.append(rew[p]-rew[1-p])
                worst=sorted(margins)[:max(1,len(margins)//10)]
                ledger=dict(ts=stamp,by='codex',task='T045',candidate=name,path=str(out),sha256=manifest['archive_sha256'],
                            opponents=list(e['opponents']),seeds_file=str(RUN/'manifest.json'),games=e['games'],wins=e['wins'],draws=e['draws'],losses=e['losses'],
                            mean_margin=e['mean_margin'],worst10_margin=sum(worst)/len(worst),errors=0,run_dir=str(RUN),
                            verdict='better' if e['recommendation_gate'] else ('worse' if ci[1]<0 else 'noise'),
                            note='No submission. Terminal uses exact final-step branch; HG uses full game when changed, otherwise exact 719-step action identity. '+verdict)
                with (SHARED/'ledger.jsonl').open('a') as f:f.write(json.dumps(ledger)+'\n')
                subprocess.run([str(SHARED/'bin/say'),'claude',message],check=True,capture_output=True,text=True)
                delivered.add(name);status.write_text(json.dumps(sorted(delivered),indent=2));print(message,flush=True)
        if len(delivered)<6:time.sleep(15)
    print('ALL SIX DELIVERED',flush=True)

if __name__=='__main__':main()
