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
        frozen=json.loads((run/'manifest.json').read_text())['exports']['exports'][f'{base}_{a.variant}']
        assert sha(source)==frozen['sha256'], 'candidate bytes differ from frozen gate'
        assert evidence['worlds']==32 and evidence['games_per_world']==[16]
        assert len(evidence['opponents'])==8 and all(v['games']==64 and v['games_per_world']==[2] for v in evidence['opponents'].values())
        archive=out/(name+'.tar.gz')
        if not archive.exists():
            temporary = archive.with_suffix('.tmp')
            with temporary.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w|',format=tarfile.GNU_FORMAT) as tar:
                data=source.read_bytes();info=tarfile.TarInfo('main.py');info.size=len(data);info.mode=0o644;info.mtime=0
                tar.addfile(info,io.BytesIO(data))
                license_path = Path('/workspace/solution_kaggri/.venv/lib/python3.12/site-packages/kaggle_environments-1.32.7.dist-info/licenses/LICENSE')
                notice = b'Contains deterministic unit execution functions from Kaggle Environments 1.32.7, Apache-2.0. Original BC/Pavel notices retained in main.py. Engine source SHA256 is recorded in manifest.json accompanying this archive.\n'
                for filename, content in (('ENGINE_LICENSE',license_path.read_bytes()),('NOTICE',notice)):
                    info=tarfile.TarInfo(filename);info.size=len(content);info.mode=0o644;info.mtime=0
                    tar.addfile(info,io.BytesIO(content))
            temporary.replace(archive)
        with tarfile.open(archive,'r:gz') as tar:
            assert tar.getnames()==['main.py','ENGINE_LICENSE','NOTICE'];assert hashlib.sha256(tar.extractfile('main.py').read()).hexdigest()==sha(source)
        manifest={'name':name,'variant':a.variant,'base':base,'source_export':str(source),'main_sha256':sha(source),
                  'archive_sha256':sha(archive),'evidence_run':str(run),'review':json.loads((HERE/'review_status.json').read_text()),
                  'exception_policy':'fail-fast: BC/HG/terminal exceptions are re-raised, never silently converted to PASS',
                  'exception_risk':'An unseen exception forfeits the whole episode instead of losing a single turn; this experimental archive intentionally keeps observable errors. Zero observed errors does not prove none will occur.',
                  'recommendation':'local gate passed; independent review required' if evidence['recommendation_gate'] else 'do not replace active pair on this evidence',
                  'source_manifest':json.loads((HERE/'manifest.json').read_text())['sources'][base],
                  'engine_sha256':json.loads((HERE/'manifest.json').read_text())['engine_sha256']}
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2));(out/'evidence.json').write_text(json.dumps(evidence,indent=2))
        shutil.copyfile(HERE/'fixtures.json',out/'fixtures.json')
        shutil.copyfile(HERE/'error_probe.json',out/'error_probe.json')
        shutil.copyfile('/workspace/shared/runs/t045_claude_execution_review_final.md',out/'CODE_REVIEW.md')
        shutil.copyfile('/workspace/shared/runs/t045_execution_loader_smoke.json',out/'loader_smoke.json')
        shutil.copyfile(run/'manifest.json',out/'gate_manifest.json')
        shutil.copyfile(run/'identity_source_hashes.json',out/'identity_source_hashes.json')
        if (run/'resource_continuation.json').exists():
            shutil.copyfile(run/'resource_continuation.json',out/'resource_continuation.json')
        shutil.copyfile(HERE/'terminal.py',out/'terminal_source.txt')
        kind={'terminal':'Только t718: распродажа остатка после последнего расходного ордера; исходные позиции рынка и все unit actions сохранены.',
              'a1':'Только HG A1: работник, чьё валидное urgent FEED уже зачтено, исключается из свободных назначений.',
              'a2':'Только HG A2: отказ от назначения, если PICKUP/путь/FEED требуют больше оставшихся до конца дня ходов. A1 выключен.'}[a.variant]
        ci=evidence['delta_score_ci95'];mc=evidence['delta_margin_ci95']
        lines=[f'# {name}', '', '**Экспериментальный frozen archive. Никаких отправок в Kaggle.**', '',kind,
               'Граница HG d0–13 сохранена. Флаги обёртки по умолчанию выключены в template; в этом архиве включён только именованный вариант. Исключения BC/HG/terminal пробрасываются, не скрываются под PASS.',
               'Риск исполнения: непредвиденное исключение приведёт к ERROR и проигрышу всего эпизода, тогда как исходный BC мог пропустить один ход. Это сознательный fail-fast вариант без скрытого PASS; ноль наблюдавшихся сбоев не гарантирует их отсутствие в новых мирах.',
               'Terminal не гарантирует неубывание cash или margin при любом сопернике: дополнительные продажи меняют общий рынок. Он сохраняет количества ранних повторных SELL и пополняет только последний SELL товара после последней траты.',
               '',f"Решение: **{manifest['recommendation']}**. Независимый code/method review: Claude PASS; review результатов силы пока pending.",
               '', '32 новых мира 929454001–929454032 × оба места × 8 замороженных соперников = 512 сравнений к собственной исходной базе.',
               'Методы оценки: ' + json.dumps(evidence['evaluation_methods'],ensure_ascii=False) + '.',
               f"W/D/L: {evidence['wins']}/{evidence['draws']}/{evidence['losses']}; score {evidence['score']:.4f}, база {evidence['baseline_score']:.4f}.",
               f"Парное изменение score: {100*evidence['delta_score']:+.3f} п.п., 95% whole-world CI [{100*ci[0]:+.3f}, {100*ci[1]:+.3f}].",
               f"Изменение margin: ${evidence['delta_margin']:+.2f}, CI [{mc[0]:+.2f}, {mc[1]:+.2f}].",
               f"Win/loss flips: {evidence['win_flips']}/{evidence['loss_flips']}; затронуто игр {evidence['changed_games']}.",
               'Ресурсы: первые 780 валидных игр сохранены; две попытки, прерванные 300-секундным host SIGALRM, оставлены в диагностике и повторены на тех же байтах/мирах. Продолжение: 10 воркеров при квоте контейнера11.52 CPU, host guard600s. Лимиты действий/банка движка не менялись. В итог входят только полные валидные результаты всех заданных ключей; детали resource_continuation.json.',
               '', 'Гейт: положительная нижняя граница score CI; нижняя граница каждого семейства не ниже −3 п.п.; ноль ошибок/timeouts/скрытых BC PASS. Эмпирический [0,0] при отсутствии flips не доказывает глобальную эквивалентность.',
               '', '| Семейство | Δscore, п.п. | 95% CI |', '|---|---:|---|']
        for family,v in evidence['families'].items():
            ci=v['delta_score_ci95'];lines.append(f"| {family} | {100*v['delta_score']:+.3f} | [{100*ci[0]:+.3f}, {100*ci[1]:+.3f}] |")
        lines += ['', 'Terminal использует точное ответвление последнего хода официального движка на каждой базовой игре; неизменённый reward воспроизводится точно. Метод проверен против четырёх полных enabled игр. A1/A2: полные игры при изменении действия; иначе точный сертификат 719/719 совпадающих действий HG при идентичном коде, отличающемся только флагами. Все предыдущие ходы terminal идентичны базе по построению.',
                  '',f"Исходные записи и команды: `{run}`; инструменты `/workspace/wt/codex/lab/t045/execution/`.",
                  f"main.py SHA256: `{sha(source)}`",f"archive SHA256: `{sha(archive)}`",'',
                  'Сохранены исходные notices BC/Pavel. Минимальная функция исполнения units с зависимостями извлечена без изменений из kaggle-environments 1.32.7 (Apache-2.0); source hash в manifest.']
        (out/'README.md').write_text('\n'.join(lines)+'\n')
        license_path=Path('/workspace/solution_kaggri/.venv/lib/python3.12/site-packages/kaggle_environments-1.32.7.dist-info/licenses/LICENSE')
        if license_path.exists():shutil.copyfile(license_path,out/'ENGINE_LICENSE')
        print(json.dumps({'candidate':name,'path':str(out),'recommendation':manifest['recommendation'],'sha256':sha(archive)}))

if __name__=='__main__':main()
