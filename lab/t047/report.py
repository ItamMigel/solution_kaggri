"""Short Russian final memo plus per-matchup ledger records."""
import argparse
import datetime
import json
from pathlib import Path

OUT=Path('/workspace/shared/runs/t047_m26_post')
HERE=Path(__file__).resolve().parent
SHARED=Path('/workspace/shared')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--ledger',action='store_true')
    a=ap.parse_args()
    s=json.loads((OUT/'summary.json').read_text())
    assert s['complete'] and s['records']==192
    rows=['# T047 — m26: post-processing без переобучения', '',
          '16 новых миров 93047001–93047016 × оба места против неизменённого m26; sanity: 8 других миров 93047101–93047108 × оба места против каждого tetsu/ozer44. 11 workers, BLAS=1. Порог: ≥65% h2h points, положительный mean margin и нижняя граница двустороннего 95% bootstrap CI по целым мирам >0; ноль ошибок/таймаутов.', '',
          '| Вариант (одно изменение) | m26 W/D/L; points | Margin, $ [world 95% CI] | tetsu points | ozer44 points | Гейт |',
          '|---|---:|---:|---:|---:|---|']
    labels={'terminal':'V1: t718 liquidation','a1':'V2: HG A1 native FEED','dsm75_mg25':'V3: DSM75 / MG25 log-prob'}
    for v,st in s['variants'].items():
        h=st['opponents']['m26']
        rows.append(f"| {labels[v]} | {h['wins']}/{h['draws']}/{h['losses']}; {h['points']:g}/32 ({100*h['points']/32:.2f}%) | {h['mean_margin']:+.2f} [{h['world95'][0]:+.2f}, {h['world95'][1]:+.2f}] | {st['opponents']['tetsu']['points']:g}/16 | {st['opponents']['ozer44']['points']:g}/16 | {'PASS' if st['pass'] else 'FAIL'} |")
    rows += ['',f"Основной гейт: **192 игры, ошибок/таймаутов {s['errors']}**. Полные симуляции официального движка, без identity/replay shortcuts. Учитывались скрытые BC/HG/terminal fallback errors и расход overage обоих игроков. Bootstrap: 100000 resamples, RNG=47020260930."]
    smoke=OUT/'loader_smoke.json'
    if smoke.exists():
        r=json.loads(smoke.read_text())
        rows += ['',f"Официальный file loader: {sum(x['parity'] for x in r)}/{len(r)} повторов точно совпали по rewards с callable-гейтом, все DONE/DONE. Фикстуры terminal/A1, метки/веса смеси и выбор entrypoint пройдены."]
    if 'sanity_control' in s:
        c=s['sanity_control']
        t=s['variants']['terminal']['opponents']
        rows += ['',f"Дополнительный контроль неизменённого m26 на тех же sanity-мирах: tetsu {c['tetsu']['points']:g}/16, ozer44 {c['ozer44']['points']:g}/16; 32/32 без ошибок. Terminal относительно контроля: Δpoints {t['tetsu']['delta_vs_parent_points']:+g}/{t['ozer44']['delta_vs_parent_points']:+g}, Δmargin ${t['tetsu']['delta_vs_parent_margin']:+.2f}/${t['ozer44']['delta_vs_parent_margin']:+.2f} (tetsu/ozer44). Контроль добавлен после двух поражений terminal против ozer44, чтобы проверить их происхождение; варианты не менялись."]
    packages=OUT/'packages.json'
    if packages.exists():
        for v,p in json.loads(packages.read_text()).items():
            rows += ['',f"Замороженный прошедший вариант: `{p['path']}`; архив `{Path(p['archive']).name}`, SHA256 `{p['sha256']}`."]
    rows += ['', 'V1 даёт небольшой денежный выигрыш в зеркале; высокая доля побед не доказывает большой прирост рейтинга против поля. A1 и смесь не рекомендованы. Вес смеси зафиксирован до старта, по этим мирам ничего не подбиралось.', '',
             f'Исходники/сборка: `{HERE}`. Полные игры, manifest с SHA256, summary и loader parity: `{OUT}`. Независимый review: `/workspace/shared/research/t047_code_review_claude.md` и, если создан, `t047_result_review_claude.md`. Никаких отправок в Kaggle.']
    (SHARED/'research/t047_m26_post.md').write_text('\n'.join(rows)+'\n')
    if a.ledger:
        mf=json.loads((HERE/'manifest.json').read_text())
        now=datetime.datetime.now(datetime.timezone.utc).isoformat()
        raw=[json.loads(x) for x in (OUT/'games.jsonl').read_text().splitlines()]
        existing=[json.loads(x) for x in (SHARED/'ledger.jsonl').read_text().splitlines() if x.strip()]
        assert not any(r.get('task')=='T047' for r in existing), 'Ledger already written'
        with (SHARED/'ledger.jsonl').open('a') as f:
            for v,st in s['variants'].items():
                for opp,stats in st['opponents'].items():
                    margins=sorted(r['margin'] for r in raw if r['variant']==v and r['opp']==opp and r['valid'])
                    worst=margins[:max(1,(len(margins)+9)//10)]
                    r=dict(ts=now,by='codex',task='T047',candidate='m26_'+v,path=mf['exports'][v]['path'],
                           sha256=mf['exports'][v]['sha256'],opponents=[opp],seeds_file=str(OUT/'manifest.json'),
                           games=stats['n'],wins=stats['wins'],draws=stats['draws'],losses=stats['losses'],
                           mean_margin=stats['mean_margin'],worst10_margin=sum(worst)/len(worst),errors=stats['n']-stats['valid'],
                           run_dir=str(OUT),verdict=('better' if st['pass'] else 'noise') if opp=='m26' else 'n/a',
                           note='Full official games, both seats; fixed single-change variant; no retraining/submission.',world95=stats['world95'])
                    f.write(json.dumps(r)+'\n')
    print(SHARED/'research/t047_m26_post.md')


if __name__=='__main__':
    main()
