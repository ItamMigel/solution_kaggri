
# ================= XS: append-only peak-window sales (T044 screen rules 3-4; lab/pavel) =================
_XS = {'rules': [('CARROT', 25, 27, 65, 16, 8, 8), ('STRAWBERRY', 20, 21, 110, 12, 6, 6)]}
_XS_PARENT = agent
del agent
_XS_STATS = {"fires": 0, "units": 0, "errors": 0}

def agent(obs, config=None):
    action = _XS_PARENT(obs, config)
    try:
        step = int(obs["step"]); day = step // 24
        if step >= 718:
            return action
        market = [list(o) if isinstance(o, (list, tuple)) else o for o in (action.get("market") or [])]
        shed = (obs.get("private") or {}).get("shed") or {}
        prices = (obs.get("market") or {}).get("prices", {}) or {}
        added = False
        for good, d0, d1, pmin, shed_min, retain, cap in _XS["rules"]:
            if len(market) >= 10 or not (d0 <= day <= d1):
                continue
            if any(isinstance(o, list) and len(o) >= 2 and o[1] == good for o in market):
                continue
            held = max(0, int(shed.get(good, 0))); price = int(prices.get(good, 0) or 0)
            if price < pmin or held < shed_min:
                continue
            q = min(cap, held - retain)
            if q > 0:
                market.append(["SELL", good, q]); added = True
                _XS_STATS["fires"] += 1; _XS_STATS["units"] += q
        if added:
            return dict(action, market=market)
        return action
    except Exception:
        _XS_STATS["errors"] += 1
        return action

agent.telemetry = _XS_STATS
