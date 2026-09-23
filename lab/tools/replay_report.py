"""Rich per-replay report built on src.replay_mine."""
import json
import sys
from collections import defaultdict

from replay_mine import mine


def main(paths, out=None):
    allres = []
    for p in paths:
        r = mine(p, verbose=False)
        allres.append(r)
        print("=" * 100)
        print(f"EPISODE {p}  seed={r['seed']}")
        for i in range(2):
            print(f"  P{i} {r['names'][i]:24s} FINAL ${r['rewards'][i]:>12,.0f}")
        for pl in range(2):
            print(f"\n### P{pl} {r['names'][pl]} ###")
            s = r["sells"][pl]
            tot = sum(v[1] for v in s.values())
            b = r["buys"][pl]
            tb = sum(v[1] for v in b.values()) + r["hire_cost"][pl] + sum(l[2] for l in r["land"][pl])
            print(f"  gross revenue ${tot:,.0f} | costs ${tb:,.0f} | net ${tot-tb:,.0f} (final ${r['rewards'][pl]:,.0f}, +3000 start)")
            print("  SELLS:")
            for k, v in sorted(s.items(), key=lambda kv: -kv[1][1]):
                print(f"    {k:11s} {v[0]:5d}u ${v[1]:>10,.0f}  avg ${v[1]/max(1,v[0]):7.1f}  d{r['first_sell_day'][pl].get(k)}+")
            print("  BUYS:")
            for k, v in sorted(b.items(), key=lambda kv: -kv[1][1]):
                print(f"    {k:22s} {v[0]:5d}u ${v[1]:>10,.0f}  avg ${v[1]/max(1,v[0]):7.1f}")
            print(f"    HIRES {sum(r['hires'][pl].values()):5d}  ${r['hire_cost'][pl]:>10,.0f}")
            print(f"    LAND  {r['land'][pl]}")
            print(f"  hands/day: {[r['hires'][pl].get(d,0) for d in range(30)]}")
            # per-day trade table
            print("  DAY  hands  money      | trades (units@avg$)")
            hist = {h[0]: h for h in r["tiles_hist"]}
            for day in range(30):
                trades = r["sell_by_day"][pl].get(day, {})
                if not trades:
                    tstr = ""
                else:
                    parts = []
                    prices = defaultdict(list)
                    for it, pr in _prices_for(r, pl, day):
                        prices[it].append(pr)
                    for it, n in sorted(trades.items(), key=lambda kv: -abs(kv[1])):
                        ps = prices.get(it, [])
                        avg = sum(ps) / len(ps) if ps else 0
                        parts.append(f"{it}:{n:+d}@{avg:.0f}")
                    tstr = " ".join(parts)
                mon = r["money"][pl][min(len(r["money"][pl]) - 1, day * 24 + 23)]
                h = hist.get(day)
                nh = h[4][pl] if h else "?"
                print(f"  d{day:<3d} {nh:<5} ${mon:>10,.0f} | {tstr}")
            print("  TILE CENSUS by day:")
            for h in r["tiles_hist"]:
                if h[0] % 3 == 0 or h[0] >= 28:
                    c = {k: v for k, v in sorted(h[1][pl].items()) if k not in ("EMPTY", "LOCKED")}
                    print(f"    d{h[0]:<3d} quads={h[5][pl]} {c}")
            print(f"  unit ops: {dict(sorted(r['unit_ops'][pl].items(), key=lambda kv: -kv[1]))}")
            print(f"  order lanes: {dict(sorted(r['order_lane'][pl].items()))}")
        print("\n  MARKET price / deficit(=I0-inv) by day:")
        for h in r["tiles_hist"]:
            if h[0] % 2 == 0 or h[0] >= 28:
                pr = {k: (v, h[3][k]) for k, v in sorted(h[2].items())}
                print(f"    d{h[0]:<3d} " + "  ".join(f"{k}=${v[0]}/{v[1]:+d}" for k, v in pr.items()))
        print(f"  shops unlocked at end: {r['tiles_hist'][-1][6]}")
    if out:
        json.dump([{k: v for k, v in r.items() if k not in ("money",)} for r in allres], open(out, "w"), default=str)


def _prices_for(r, pl, day):
    return r["sell_price_by_day"][pl].get(day, [])


if __name__ == "__main__":
    main(sys.argv[1:])
