"""Freeze only passing, independently reviewed T047 variants. Never submit."""
import argparse
import gzip
import hashlib
import io
import json
import shutil
import tarfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=Path('/workspace/shared/runs/t047_m26_post')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--review',type=Path,required=True)
    a=ap.parse_args()
    assert a.review.is_file()
    summary=json.loads((OUT/'summary.json').read_text())
    assert summary['complete'] and summary['errors']==0
    control=[json.loads(x) for x in (OUT/'sanity_control.jsonl').read_text().splitlines()]
    assert len(control)==32 and all(r['valid'] for r in control)
    smoke=json.loads((OUT/'loader_smoke.json').read_text())
    assert len(smoke)==6 and all(r['parity'] for r in smoke)
    manifest=json.loads((HERE/'manifest.json').read_text())
    result={}
    for variant,stats in summary['variants'].items():
        if not stats['pass']:
            continue
        name='t047_m26_'+variant
        target=Path('/workspace/shared/candidates')/name
        assert not target.exists(), 'Frozen candidate already exists'
        source=HERE/'exports'/variant/'main.py'
        assert sha(source)==manifest['exports'][variant]['sha256']
        (target/'pkg').mkdir(parents=True)
        shutil.copyfile(source,target/'pkg/main.py')
        (target/'evidence').mkdir()
        for path in (OUT/'manifest.json',OUT/'provenance.json',OUT/'summary.json',OUT/'games.jsonl',OUT/'sanity_control.jsonl',OUT/'loader_smoke.json',HERE/'fixtures.json',a.review):
            shutil.copyfile(path,target/'evidence'/path.name)
        code_review=Path('/workspace/shared/research/t047_code_review_claude.md')
        if code_review.is_file() and code_review!=a.review:
            shutil.copyfile(code_review,target/'evidence'/code_review.name)
        # Reproducible archive with main.py at its root.
        archive=target/(name+'.tar.gz')
        data=source.read_bytes()
        with archive.open('wb') as f, gzip.GzipFile(fileobj=f,mode='wb',mtime=0,filename='') as gz, tarfile.open(fileobj=gz,mode='w') as tar:
            ti=tarfile.TarInfo('main.py')
            ti.size=len(data)
            ti.mode=0o644
            ti.mtime=0
            tar.addfile(ti,io.BytesIO(data))
        with tarfile.open(archive) as tar:
            assert tar.getnames()==['main.py'] and tar.extractfile('main.py').read()==data
        h=stats['opponents']['m26']
        description={
            'terminal':'T045 liquidation на шаге 718, после native unit actions; сохраняет рыночный префикс и лимит 10 ордеров. До шага 718 поведение родителя сохранено. Terminal при исключении возвращает действие родителя.',
            'a1':'HG A1: работник, уже выполняющий native urgent FEED, исключается из повторного назначения HG.',
            'dsm75_mg25':'взвешенная смесь log-prob ансамблей DSM 75% / Mother-Goose 25%; веса моделей исходные, изменена только метка двух дополнительных членов.',
        }[variant]
        text=f'''# {name}

Пройден заданный T047 гейт; никаких отправок в Kaggle.

Основа: Pavel m26dsm, o28_dsm_cn, HG d13, fill. Единственное изменение: {description} Переобучения нет. Исходный fallback сохранён.

Против неизменённого m26: {h['wins']}/{h['draws']}/{h['losses']} W/D/L, {h['points']}/32 points, средний margin ${h['mean_margin']:+.2f}, whole-world 95% CI [{h['world95'][0]:+.2f}, {h['world95'][1]:+.2f}]. Миры 93047001–93047016, оба места; 100000 фиксированных bootstrap resamples.

Sanity, миры 93047101–93047108, оба места: tetsu {stats['opponents']['tetsu']['points']}/16 points; ozer44 {stats['opponents']['ozer44']['points']}/16. Производительность sanity не входила в формальный порог; контроль неизменённого m26 на тех же мирах: tetsu {summary['sanity_control']['tetsu']['points']}/16, ozer44 {summary['sanity_control']['ozer44']['points']}/16. В полном гейте 192/192 и в дополнительных 32/32 контрольных играх нет ошибок/таймаутов; 6/6 повторов через официальный file loader совпадают с callable rewards. Независимый review: evidence/{a.review.name}.

Размер эффекта указан в долларах выше. Высокая доля побед в зеркале не доказывает большой прирост рейтинга или побед против всего поля.

Архив: {archive.name}; внутри только main.py. Файлы evidence фиксируют исходники, миры, результаты и проверки. Человек принимает решение о возможной отправке самостоятельно.
'''
        (target/'README.md').write_text(text)
        hashes={str(p.relative_to(target)):sha(p) for p in sorted(target.rglob('*')) if p.is_file()}
        (target/'sha256.json').write_text(json.dumps(hashes,indent=2))
        result[variant]={'path':str(target),'archive':str(archive),'sha256':sha(archive),'source_sha256':sha(source)}
    (OUT/'packages.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
