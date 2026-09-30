"""Freeze only complete PASS results with independent review and loader parity."""
import argparse
import gzip
import hashlib
import io
import json
import shutil
import statistics
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
        for p in (OUT/'manifest.json',OUT/'summary.json',OUT/'games.jsonl',OUT/'loader_smoke.json',OUT/'attribution.json',OUT/'provenance.json',
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

Формальный T048-B PASS. Никаких отправок в Kaggle; решение остаётся у человека.

База: frozen t047_m26_terminal, SHA256 {manifest['base']['sha256']}.
Включён только {variant}. Веса сохранены. На данном observation wrapper не меняет
unit actions и собственный рыночный префикс расходов; дальнейшая BC-политика может
реагировать на изменившиеся деньги. Прогнозы и код: evidence/source/postprocess.py.

16 новых h2h-миров, оба места: {h['wins']}/{h['draws']}/{h['losses']} W/D/L,
{h['points']}/32 points. Средняя мировая маржа ${h['mean_margin']:+.2f}; 95%world CI
[{h['margin_world95'][0]:+.2f}, {h['margin_world95'][1]:+.2f}].
Медиана ${statistics.median(h['world_margins']):+.2f}; наибольший мир
${max(h['world_margins']):+.2f} сильно влияет на среднее.

Sanity 8 новых миров на соперника, оба места: tetsu {t['points']}/16,
парная Δмаржа ${t['paired_control']['delta_margin']:+.2f}; ozer44 {o['points']}/16,
парная Δмаржа ${o['paired_control']['delta_margin']:+.2f}. Ни points, ни средняя
маржа не ухудшились против paired unchanged-base controls. Это конечный screen,
а не статистическое доказательство non-inferiority или прогноз рейтинга.

Синтетические сценарии соперника (наша очередь и склад ×0.5/1/1.5) особенно
подходят зеркалу. Малые денежные улучшения превращают зеркальные ничьи в победы;
87.5% h2h points не означает сопоставимого усиления против ладдера. expected_gain
является предсказанием этого prior, а не измеренной прямой прибылью. Factual-state
one-step deltas в attribution.json не раскладывают полную альтернативную игру.
Свой остаток товара одинаков, но чужая BUY-affordability и shared inventory могут
изменяться даже вне ценового пола; будущее value всей системы не константа.

160/160 полных official gate игр валидны, ошибок/таймаутов 0. 6/6 official file-loader
повторов совпали с callable rewards; 1,438 off-mode actions совпали с базой.
Максимальный callback кандидата {stats['max_call']:.6f}s; суммарный overage {stats['overage']:.6f}s.
Wrapper при исключении возвращает base action со счётчиком; ошибок в гейте нет.
Независимые code/result reviews приложены. late_ev отвергнут и не включён.

Архив {archive.name} содержит только main.py. SHA256: {sha(archive)}.
Автоматической замены champion нет; перенос на широкое поле не доказан.
''')
        (target/'sha256.json').write_text(json.dumps({str(p.relative_to(target)):sha(p) for p in sorted(target.rglob('*')) if p.is_file()},indent=2))
        result[variant]=dict(path=str(target),archive=str(archive),sha256=sha(archive),source_sha256=sha(source))
    (OUT/'packages.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
