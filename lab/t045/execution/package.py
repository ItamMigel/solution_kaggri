"""Freeze reviewed bytes with evidence, never submit anything."""
import argparse
import gzip
import hashlib
import io
import json
import shutil
import tarfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=Path('/workspace/shared/candidates')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);ap.add_argument('--variant',required=True,choices=['terminal','a1','a2'])
    a=ap.parse_args();run=Path(a.run);summary=json.loads((run/'summary.json').read_text())
    assert summary['errors']==0
    for base in ('m15ens','mix4'):
        name=f't045_{base}_{a.variant}'
        evidence=summary['results'][f'{base}_{a.variant}'];assert evidence['games']==512
        out=OUT/name;out.mkdir(exist_ok=True)
        source=HERE/'exports'/f'{base}_{a.variant}.py'
        archive=out/(name+'.tar.gz')
        if not archive.exists():
            with archive.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w|',format=tarfile.GNU_FORMAT) as tar:
                data=source.read_bytes();info=tarfile.TarInfo('main.py');info.size=len(data);info.mode=0o644;info.mtime=0
                tar.addfile(info,io.BytesIO(data))
        with tarfile.open(archive,'r:gz') as tar:
            assert tar.getnames()==['main.py'];assert hashlib.sha256(tar.extractfile('main.py').read()).hexdigest()==sha(source)
        manifest={'name':name,'variant':a.variant,'base':base,'source_export':str(source),'main_sha256':sha(source),
                  'archive_sha256':sha(archive),'evidence_run':str(run),'review':'pending independent Claude review',
                  'recommendation':'local gate passed; independent review required' if evidence['recommendation_gate'] else 'do not replace active pair on this evidence',
                  'source_manifest':json.loads((HERE/'manifest.json').read_text())['sources'][base],
                  'engine_sha256':json.loads((HERE/'manifest.json').read_text())['engine_sha256']}
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2));(out/'evidence.json').write_text(json.dumps(evidence,indent=2))
        shutil.copyfile(HERE/'fixtures.json',out/'fixtures.json')
        shutil.copyfile(run/'manifest.json',out/'gate_manifest.json')
        shutil.copyfile(HERE/'terminal.py',out/'terminal_source.txt')
        kind={'terminal':'Только t718: распродажа остатка после последнего расходного ордера; исходные позиции рынка и все unit actions сохранены.',
              'a1':'Только HG A1: работник, чьё валидное urgent FEED уже зачтено, исключается из свободных назначений.',
              'a2':'Только HG A2: отказ от назначения, если PICKUP/путь/FEED требуют больше оставшихся до конца дня ходов. A1 выключен.'}[a.variant]
        ci=evidence['delta_score_ci95'];mc=evidence['delta_margin_ci95']
        lines=[f'# {name}', '', '**Экспериментальный frozen archive. Никаких отправок в Kaggle.**', '',kind,
               'Граница HG d0–13 сохранена. Флаги обёртки по умолчанию выключены в template; в этом архиве включён только именованный вариант. Исключения BC/HG/terminal пробрасываются, не скрываются под PASS.',
               '',f"Решение: **{manifest['recommendation']}**. Независимый review: pending Claude.",
               '', '32 новых мира 929452001–929452032 × оба места × 8 замороженных соперников = 512 сравнений к собственной исходной базе.',
               f"W/D/L: {evidence['wins']}/{evidence['draws']}/{evidence['losses']}; score {evidence['score']:.4f}, база {evidence['baseline_score']:.4f}.",
               f"Парное изменение score: {100*evidence['delta_score']:+.3f} п.п., 95% whole-world CI [{100*ci[0]:+.3f}, {100*ci[1]:+.3f}].",
               f"Изменение margin: ${evidence['delta_margin']:+.2f}, CI [{mc[0]:+.2f}, {mc[1]:+.2f}].",
               f"Win/loss flips: {evidence['win_flips']}/{evidence['loss_flips']}; затронуто игр {evidence['changed_games']}.",
               '', 'Гейт: положительная нижняя граница score CI; нижняя граница каждого семейства не ниже −3 п.п.; ноль ошибок/timeouts/скрытых BC PASS. Эмпирический [0,0] при отсутствии flips не доказывает глобальную эквивалентность.',
               '', '| Семейство | Δscore, п.п. | 95% CI |', '|---|---:|---|']
        for family,v in evidence['families'].items():
            ci=v['delta_score_ci95'];lines.append(f"| {family} | {100*v['delta_score']:+.3f} | [{100*ci[0]:+.3f}, {100*ci[1]:+.3f}] |")
        lines += ['', 'Terminal использует точное ответвление последнего хода официального движка на каждой базовой игре; неизменённый reward воспроизводится точно. Метод проверен против четырёх полных enabled игр. A1/A2 — отдельные полные игры. Все предыдущие ходы terminal идентичны базе по построению.',
                  '',f"Исходные записи и команды: `{run}`; инструменты `/workspace/wt/codex/lab/t045/execution/`.",
                  f"main.py SHA256: `{sha(source)}`",f"archive SHA256: `{sha(archive)}`",'',
                  'Сохранены исходные notices BC/Pavel. Минимальная функция исполнения units с зависимостями извлечена без изменений из kaggle-environments 1.32.7 (Apache-2.0); source hash в manifest.']
        (out/'README.md').write_text('\n'.join(lines)+'\n')
        license_path=Path('/workspace/solution_kaggri/.venv/lib/python3.12/site-packages/kaggle_environments-1.32.7.dist-info/licenses/LICENSE')
        if license_path.exists():shutil.copyfile(license_path,out/'ENGINE_LICENSE')
        print(json.dumps({'candidate':name,'path':str(out),'recommendation':manifest['recommendation'],'sha256':sha(archive)}))

if __name__=='__main__':main()
