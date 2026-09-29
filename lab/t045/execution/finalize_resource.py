"""Preserve all attempts; retry explicit host alarms once, without reward selection."""
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
HERE=Path(__file__).resolve().parent
RUN=Path('/workspace/shared/runs/t045_execution_gate32_final')
LOG=Path('/workspace/shared/runs/t045_execution_gate32_final.log')

def main():
    while 'DONE' not in LOG.read_text().splitlines():
        time.sleep(15)
    while not (RUN/'retry_games.jsonl').exists() or len((RUN/'retry_games.jsonl').read_text().splitlines())<2:
        time.sleep(15)
    original_lines=(RUN/'games.jsonl').read_text().splitlines()
    rows=[json.loads(x) for x in original_lines]
    retries=[json.loads(x) for x in (RUN/'retry_games.jsonl').read_text().splitlines()]
    key=lambda r:tuple(r[k] for k in ('base','variant','opp','seed','seat'))
    assert len(rows)==3072 and len({key(r) for r in rows})==3072
    assert len(retries)==2 and all(r['valid'] and r['counts'].get('host_alarm_fired',0)==0 for r in retries)
    invalid=[r for r in rows if not r['valid']]
    assert all(r['counts'].get('host_alarm_fired')==1 for r in invalid), 'non-host failure blocks delivery'
    existing={key(r) for r in retries}
    assert existing <= {key(r) for r in invalid}
    additional=[r for r in invalid if key(r) not in existing]
    if additional:
        import gate
        os.environ['T045_WALL_LIMIT']='3600'
        resource=json.loads((RUN/'resource_continuation.json').read_text())
        resource['excluded_attempts']+=additional
        (RUN/'resource_continuation.json').write_text(json.dumps(resource,indent=2))
        jobs=[list(key(r))+[False] for r in additional]
        with (RUN/'additional_retry_games.jsonl').open('x',buffering=1) as f,ProcessPoolExecutor(max_workers=2) as pool:
            for future in as_completed([pool.submit(gate.game,j) for j in jobs]):
                r=future.result();f.write(json.dumps(r)+'\n');retries.append(r)
        assert all(r['valid'] and not r['counts'].get('host_alarm_fired',0) for r in retries), '3600s retry failure blocks delivery'
    assert {key(r) for r in invalid}=={key(r) for r in retries}
    backup=RUN/'games_with_infrastructure_attempts.jsonl'
    assert not backup.exists()
    backup.write_bytes((RUN/'games.jsonl').read_bytes())
    replacement={key(r):r for r in retries}
    (RUN/'games.jsonl').write_text(''.join((line if r['valid'] else json.dumps(replacement[key(r)]))+'\n' for line,r in zip(original_lines,rows)))
    print(f'CONSOLIDATED: 3072 valid unique records; {len(invalid)} main-run invalid attempts preserved separately',flush=True)
    subprocess.run([sys.executable,str(HERE/'report.py'),str(RUN)],check=True)
    subprocess.run([sys.executable,str(HERE/'verify_delivery.py'),str(RUN),'--evaluation-only'],check=True)
    print('EVALUATION READY: independent results review required before archives',flush=True)

if __name__=='__main__':main()
