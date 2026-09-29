"""Wait for closed writers, preserve failed attempts, consolidate identical-key retries."""
import json
import subprocess
import sys
import time
from pathlib import Path
HERE=Path(__file__).resolve().parent
RUN=Path('/workspace/shared/runs/t045_execution_gate32_final')
LOG=Path('/workspace/shared/runs/t045_execution_gate32_final.log')
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
assert len(invalid)==2 and {key(r) for r in invalid}=={key(r) for r in retries}
assert all(r['counts'].get('host_alarm_fired')==1 for r in invalid)
backup=RUN/'games_with_infrastructure_attempts.jsonl'
assert not backup.exists()
backup.write_bytes((RUN/'games.jsonl').read_bytes())
replacement={key(r):r for r in retries}
accepted=[r if r['valid'] else replacement[key(r)] for r in rows]
assert all(r['valid'] for r in accepted)
(RUN/'games.jsonl').write_text(''.join((line if r['valid'] else json.dumps(replacement[key(r)]))+'\n' for line,r in zip(original_lines,rows)))
print('CONSOLIDATED: 3072 valid unique records, all4 failed attempts retained separately',flush=True)
subprocess.run([sys.executable,str(HERE/'watch_delivery.py')],check=True)
subprocess.run([sys.executable,str(HERE/'verify_delivery.py'),str(RUN)],check=True)
