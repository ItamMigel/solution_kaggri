"""Default-off final-tick liquidation. No market-prefix reorder or new spending."""
import copy

PRODUCTS = ('WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON', 'EGG', 'MILK', 'WOOL', 'FERTILIZER')


def post_unit_shed(obs, action, config, engine):
    farm = copy.deepcopy(obs['farms'][obs['player']])
    private = copy.deepcopy(obs['private'])
    cfg = config or {}
    size = int(cfg.get('boardSize', 10))
    turns = int(cfg.get('turnsPerDay', 24))
    capacity = int(cfg.get('shedCapacity', 100))
    actions = [action.get('farmer', ['PASS'])] + list(action.get('hands', []))
    # Match interpreter's atomic over-demand PLANT guard before sequential units.
    demand = {}
    for a in actions:
        if a and a[0] == 'PLANT' and len(a) >= 2:
            demand[a[1]] = demand.get(a[1], 0) + 1
    blocked = {it for it, n in demand.items() if n > private['seeds'].get(it, 0)}
    for i, a in enumerate(actions):
        if a and a[0] == 'PLANT' and len(a) >= 2 and a[1] in blocked:
            a = ['PASS']
        engine['_apply_unit_action'](farm, private, i, a, size, int(obs['step']) // turns, turns, capacity)
    return private['shed']


def liquidate(obs, action, config, engine, enabled=False):
    if not enabled or int(obs['step']) != 718:
        return action
    cfg = config or {}
    cap = int(cfg.get('shedCapacity', 100))
    limit = int(cfg.get('maxMarketOrdersPerTurn', 10))
    orders = action.get('market', [])
    if not isinstance(orders, list) or len(orders) > limit:
        return action
    shed = post_unit_shed(obs, action, cfg, engine)
    result = copy.deepcopy(action)
    orders = result.setdefault('market', [])
    # Freeze through the last spending/unknown order: enlarged sales before a
    # BUY/HIRE could change its fill and subsequent prefix funding/capacity.
    boundary = -1
    for i, order in enumerate(orders):
        if not (isinstance(order, list) and order and order[0] in ('SELL', 'NOOP')):
            boundary = i
    left = {it: int(shed.get(it, 0)) for it in PRODUCTS}
    for i, order in enumerate(orders):
        if not isinstance(order, list) or len(order) < 3:
            continue
        op, it, q = order[:3]
        if it not in left:
            continue
        q = max(0, int(q))
        if op == 'BUY_PRODUCT' and it in ('WHEAT', 'FERTILIZER'):
            # Upper bound: actual buy fill depends on the hidden opponent and
            # simultaneous prices. Saturating SELL is safe for any actual fill.
            left[it] = min(cap, left[it] + q)
        elif op == 'SELL':
            if i > boundary and q > 0:
                order[2] = max(q, left[it])
            left[it] = max(0, left[it] - max(0, int(order[2])))
    prices = obs.get('market', {}).get('prices', {})
    missing = sorted((it for it in PRODUCTS if left[it] > 0),
                     key=lambda it: (-left[it] * float(prices.get(it, 1)), PRODUCTS.index(it)))
    for it in missing[:max(0, limit - len(orders))]:
        orders.append(['SELL', it, left[it]])
    return result
