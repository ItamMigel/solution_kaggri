"""Lockstep official env vs gpuenv; compare feat.py(obs) against gpufeat(State) at every step for both players.
usage: python parity_test.py [--seed S] [--agents A,B] [--steps N]"""
import argparse, copy, json, os, sys
import numpy as np, torch
torch.backends.cudnn.allow_tf32 = False; torch.backends.cuda.matmul.allow_tf32 = False  # exact fp32 for parity tests (H100 defaults to TF32 convs)
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "bc")); sys.path.insert(0, os.path.join(HERE, ".."))
import feat, gpufeat
from gpuenv.env import VecKaggriculture
from gpuenv._encode import encode_actions
from kaggle_environments import make

def obs_at(steps, t, p):
    o = copy.deepcopy(steps[t][p]["observation"]); sh = steps[t][0]["observation"]
    for k in ("step", "day", "hour", "farms", "market", "town"):
        if k not in o and k in sh: o[k] = sh[k]
    o["player"] = p; return o

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=851094592)
    ap.add_argument("--agents", default="/workspace/wt/claude/agents/horizon_v5_market.py,/workspace/wt/claude/agents/horizon_v4.py")
    ap.add_argument("--steps", type=int, default=719); a = ap.parse_args()
    env = make("kaggriculture", configuration={"seed": a.seed}); env.run(a.agents.split(",")); steps = env.steps
    dev = "cuda"; ve = VecKaggriculture(1, device=dev, cuda_graph=False); st = ve.reset(torch.tensor([a.seed], device=dev))
    so = gpufeat.ShopOrder(1, dev); worst = {}
    for t in range(min(a.steps, len(steps) - 1)):
        so.update(st)
        for p in range(2):
            o = obs_at(steps, t, p)
            B_ref = feat.board_tensor(o, p); G_ref = feat.glob_vec(o, p); U_ref = feat.unit_list(o, p)
            B, G, uv, ux, uy, um = gpufeat.features(st, p, so)
            B = B[0].cpu().numpy(); G = G[0].cpu().numpy()
            db = np.abs(B - B_ref); dg = np.abs(G - G_ref)
            nu = int(um[0].sum()); du = max([float(np.abs(uv[0, i].cpu().numpy() - U_ref[i][2]).max()) for i in range(len(U_ref))] + [0.0])
            for name, d, extra in (("board", db.max(), np.unravel_index(db.argmax(), db.shape)), ("glob", dg.max(), int(dg.argmax())), ("units", du, (nu, len(U_ref)))):
                if d > worst.get(name, (0,))[0]: worst[name] = (float(d), t, p, str(extra))
            if nu != len(U_ref): worst["unit_count"] = (1.0, t, p, f"{nu} vs {len(U_ref)}")
        acts = [[steps[t + 1][0]["action"], steps[t + 1][1]["action"]]]
        st, r, done, info = ve.step(st, encode_actions(acts, device=dev))
    print(json.dumps(worst, indent=1))
