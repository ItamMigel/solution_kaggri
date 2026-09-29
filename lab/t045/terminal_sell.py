"""Research-only final-tick liquidation; preserve existing order indices."""
import copy

PRODUCTS = ('WHEAT', 'CARROT', 'MELON', 'STRAWBERRY', 'TOMATO', 'EGG', 'MILK', 'WOOL', 'FERTILIZER')


def top_up(action, post_unit_shed, prices):
    result = copy.deepcopy(action)
    orders = result.setdefault('market', [])
    left = {p: int(post_unit_shed.get(p, 0)) for p in PRODUCTS}
    # Keep every pre-existing slot (including NOOP and buy orders) in place.
    for order in orders[:10]:
        if isinstance(order, list) and len(order) >= 3 and order[0] == 'SELL' and order[1] in left:
            item = order[1]
            order[2] = max(int(order[2]), left[item])
            left[item] = 0
    missing = [p for p in PRODUCTS if left[p] > 0]
    missing.sort(key=lambda p: -left[p] * float(prices.get(p, 1)))
    for item in missing[:max(0, 10 - len(orders))]:
        orders.append(['SELL', item, left[item]])
    return result


def replay_terminal_audit(replay_path):
    import contextlib
    import gzip
    import io
    import json
    from types import SimpleNamespace
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import kaggle_environments.envs.kaggriculture.kaggriculture as K
    with gzip.open(replay_path, 'rt') as f:
        d = json.load(f)
    before = d['steps'][-2]
    recorded = d['steps'][-1]
    assert before[0]['observation']['step'] == 718
    actions = [copy.deepcopy(s['action']) for s in recorded]

    def run(which=None):
        obs = copy.deepcopy(before[0]['observation'])
        farms, market = obs['farms'], obs['market']
        priv = [copy.deepcopy(s['observation']['private']) for s in before]
        act = copy.deepcopy(actions)
        for p in (0, 1):
            ua = [act[p].get('farmer', ['PASS'])] + act[p].get('hands', [])
            demand = {}
            for a in ua:
                if a and a[0] == 'PLANT':
                    demand[a[1]] = demand.get(a[1], 0) + 1
            for i, a in enumerate(ua):
                if a and a[0] == 'PLANT' and demand[a[1]] > priv[p]['seeds'].get(a[1], 0):
                    a = ['PASS']
                K._apply_unit_action(farms[p], priv[p], i, a, 10, 29, 24, 100)
        if which is not None:
            act[which] = top_up(act[which], priv[which]['shed'], market['prices'])
        state = [SimpleNamespace(action=act[p], observation=SimpleNamespace(
            farms=farms, market=market, private=priv[p])) for p in (0, 1)]
        K._process_market(state, SimpleNamespace(configuration=d['configuration']))
        return [f['money'] for f in farms], act, [p['shed'] for p in priv]

    money, _, _ = run()
    assert money == d['rewards'], (replay_path, money, d['rewards'])
    results = []
    for p, name in enumerate(d['info']['TeamNames']):
        new, act, shed = run(p)
        results.append(dict(name=name, seat=p, before=money, after=new,
                            delta_cash=new[p]-money[p],
                            delta_margin=(new[p]-new[1-p])-(money[p]-money[1-p]),
                            market_before=actions[p]['market'], market_after=act[p]['market'], shed_after=shed[p]))
    return dict(episode=d['info']['EpisodeId'], exact_baseline=True, results=results)


if __name__ == '__main__':
    import json
    from pathlib import Path
    rows = [replay_terminal_audit(p) for p in Path('/workspace/shared/research/t045_replays').glob('*.gz')]
    out = Path('/workspace/shared/research/t045_terminal_audit.json')
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(json.dumps(rows, ensure_ascii=False, indent=2))
