"""top-RE agent entry (bundled into a single main.py by bundle.py).
Pipeline per turn: plan.desired -> market.orders -> units.act."""
def agent(obs, config=None):
    player = int(obs["player"])
    want = plan_desired(obs, player)
    tg = plan_targets(obs, player)
    try:
        market = market_orders(obs, player, want, tg)
    except Exception:
        market = []
    try:
        farmer, hands = units_act(obs, {"player": player, "want": want, "targets": tg, "market": market})
    except Exception:
        farmer, hands = ["PASS"], [["PASS"] for _ in obs["farms"][player].get("hands") or []]
    return {"farmer": farmer, "hands": hands, "market": market}
