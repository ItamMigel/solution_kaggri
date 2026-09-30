"""Freeze only complete PASS results with independent review and loader parity."""
import argparse
import gzip
import hashlib
import io
import json
import shutil
import tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=Path('/workspace/shared/runs/t048_ev_gate')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--code-review',type=Path,required=True)
    ap.add_argument('--result-review',type=Path,required=True);a=ap.parse_args()
    assert a.code_review.is_file() and a.result_review.is_file()
    summary=json.loads((OUT/'summary.json').read_text())
    assert summary['complete'] and summary['records']==160 and summary['errors']==0
    smoke=json.loads((OUT/'loader_smoke.json').read_text())
    assert len(smoke)==6 and all(r['parity'] for r in smoke)
    assert sum(r.get('identity_calls',0) for r in smoke)==1438
    assert not any(r.get('identity_diffs',[]) for r in smoke)
    manifest=json.loads((OUT/'manifest.json').read_text())['build']
    result={}
    for variant,stats in summary['variants'].items():
        if not stats['passed']:continue
        source=HERE/'exports'/variant/'main.py'
        assert sha(source)==manifest['exports'][variant]['sha256']
        name='t048_m26_'+variant;target=Path('/workspace/shared/candidates')/name
        assert not target.exists(),'Frozen candidate already exists; do not overwrite'
        (target/'pkg').mkdir(parents=True);(target/'evidence').mkdir()
        shutil.copyfile(source,target/'pkg/main.py')
        for p in (OUT/'manifest.json',OUT/'summary.json',OUT/'games.jsonl',OUT/'loader_smoke.json',
                  HERE/'fixtures.json',a.code_review,a.result_review):
            shutil.copyfile(p,target/'evidence'/p.name)
        shutil.copytree(OUT/'source',target/'evidence/source')
        archive=target/(name+'.tar.gz');data=source.read_bytes()
        with archive.open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as gz,tarfile.open(fileobj=gz,mode='w') as tar:
            ti=tarfile.TarInfo('main.py');ti.size=len(data);ti.mode=0o644;ti.mtime=0
            tar.addfile(ti,io.BytesIO(data))
        with tarfile.open(archive) as tar:
            assert tar.getnames()==['main.py'] and tar.extractfile('main.py').read()==data
        h=stats['opponents']['base'];t=stats['opponents']['tetsu'];o=stats['opponents']['ozer44']
        (target/'README.md').write_text(f'''# {name}

Formal T048-B PASS. Never submitted to Kaggle; human decides any use.

Base: frozen t047_m26_terminal, sha256 {manifest['base']['sha256']}.
Only wrapper mode {variant} is enabled. Weights/units/native funding prefix remain unchanged.
Code and expected-value assumptions: evidence/source/postprocess.py and independent reviews.

Fresh h2h16 worlds, both seats: {h['wins']}/{h['draws']}/{h['losses']} W/D/L;
{h['points']}/32 points. Mean margin ${h['mean_margin']:+.2f}; world95%CI
[{h['margin_world95'][0]:+.2f}, {h['margin_world95'][1]:+.2f}].
Sanity8 worlds each, both seats: tetsu {t['points']}/16 (paired margin delta
${t['paired_control']['delta_margin']:+.2f}); ozer44 {o['points']}/16
(paired delta ${o['paired_control']['delta_margin']:+.2f}). Neither observed points
nor mean margin declined versus paired unchanged-base controls. This is a finite
sanity screen, not a statistical non-inferiority guarantee or a rating forecast.

160/160 full official gate games valid,0 errors/timeouts.6/6 official file-loader
comparisons match callable rewards;1,438 off-mode action comparisons match base.
Candidate max measured callback {stats['max_call']:.6f}s; overage sum {stats['overage']:.6f}s.
Errors in the wrapper fail open to the base action and are counted; no error was accepted.

Archive {archive.name} contains only main.py. SHA256: {sha(archive)}.
High points in near-mirror games can reflect small cash tie-breaking. No automatic
replacement of the champion and no promotion claim against the broad ladder.
''')
        (target/'sha256.json').write_text(json.dumps({str(p.relative_to(target)):sha(p) for p in sorted(target.rglob('*')) if p.is_file()},indent=2))
        result[variant]=dict(path=str(target),archive=str(archive),sha256=sha(archive),source_sha256=sha(source))
    (OUT/'packages.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
