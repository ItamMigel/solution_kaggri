"""End-to-end: exported numpy agent (official engine) vs GPU policy (gpuenv), greedy, same seed, both seats.
Reports first step where money/actions diverge. usage: python e2e_test.py --ckpt X --team dsm [--seed S]"""
import argparse, json, os, subprocess, sys, torch
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import policy, gpufeat
from gpuenv.env import VecKaggriculture
from gpuenv import ops as O
from kaggle_environments import make
ap = argparse.ArgumentParser(); ap.add_argument("--ckpt", required=True); ap.add_argument("--team", default="dsm"); ap.add_argument("--seed", type=int, default=851094592)
ap.add_argument("--agent", default="/tmp/e2e_agent_main.py"); a = ap.parse_args()
subprocess.run([sys.executable, os.path.join(HERE, "..", "bc", "export.py"), "--ckpt", a.ckpt, "--team", a.team, "--out", a.agent], check=True)
env = make("kaggriculture", configuration={"seed": a.seed}); env.run([a.agent, a.agent]); steps = env.steps
dev = "cuda" if torch.cuda.is_available() else "cpu"
ck = torch.load(a.ckpt, map_location=dev); net = policy.PolicyNet(ck["gdim"]).to(dev); net.load_state_dict(ck["state"], strict=False); net.eval()
teams = ck.get("teams", ["mmpq", "dsm", "mgoose"]); team = torch.zeros((1, len(teams)), device=dev); team[0, teams.index(a.team)] = 1
ve = VecKaggriculture(1, device=dev, cuda_graph=False); st = ve.reset(torch.tensor([a.seed], device=dev)); so = gpufeat.ShopOrder(1, dev)
first = None; n_act_diff = 0
with torch.no_grad():
    for t in range(len(steps) - 1):
        so.update(st)
        outs = [policy.act(net, st, p, so, team, greedy=True) for p in (0, 1)]
        acts = policy.combine(outs[0][0], outs[1][0])
        for p in (0, 1):
            ref = steps[t + 1][p]["action"] or {}
            nh = int(st.n_hands[0, p])
            got_units = [O.decode_unit_action(acts.farmer[0, p].tolist())] + [O.decode_unit_action(acts.hands[0, p, j].tolist()) for j in range(nh)]
            ref_units = [ref.get("farmer") or ["PASS"]] + list(ref.get("hands") or [])
            norm = lambda u: [u[0]] + ([u[1]] if len(u) > 1 else []) + ([int(u[2])] if len(u) > 2 else [])
            got_mkt = [x for x in (O.decode_market_order(acts.market[0, p, j].tolist()) for j in range(O.MAX_ORDERS)) if x]
            same = [norm(u) for u in got_units] == [norm(u) for u in ref_units[:len(got_units)]] and got_mkt == [list(x) for x in (ref.get("market") or [])]
            if not same:
                n_act_diff += 1
                if first is None:
                    first = (t, p); print("FIRST ACTION DIFF step", t, "player", p); print(" official:", json.dumps(ref)[:400]); print(" gpu     :", json.dumps({"units": got_units, "market": got_mkt})[:400])
        st, *_ = ve.step(st, acts)
        m_ref = [steps[t + 1][p]["observation"]["farms"][p]["money"] if "farms" in steps[t + 1][p]["observation"] else steps[t + 1][0]["observation"]["farms"][p]["money"] for p in (0, 1)]
        m_gpu = st.money[0].tolist()
        if [int(x) for x in m_ref] != m_gpu and first is None:
            first = (t, "money"); print("MONEY DIFF step", t, m_ref, m_gpu)
print("final official", env.state[0]["reward"], env.state[1]["reward"], "| gpu", st.money[0].tolist(), "| action-diff player-steps:", n_act_diff)
