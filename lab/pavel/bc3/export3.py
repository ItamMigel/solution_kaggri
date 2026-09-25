"""Export BC v3 checkpoint(s) to ONE self-contained numpy-only Kaggle agent file (main.py).
Weights are embedded (float16, zlib, base85); feat.py / feat3.py and the torch-free agent code of agent3.py are embedded
verbatim (base64), so the file needs only numpy and the standard library and never reads other files.

usage: python export3.py --ckpt a.pt[,b.pt,...] --out /path/main.py [--fill --smask --team mgoose_cn ...]
The exported file is the candidate: evaluate it directly with compare.py; parity_np.py checks it against torch."""
import argparse, base64, io, json, os, re, sys, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FEAT_PY = os.path.join(HERE, "..", "..", "bc", "feat.py")

NP_MODEL = r'''
def _np_conv3(x, w, b):
    c, H, Wd = x.shape; o = w.shape[0]
    xp = np.pad(x, ((0, 0), (1, 1), (1, 1)))
    cols = np.stack([xp[:, i:i + H, j:j + Wd] for i in range(3) for j in range(3)], 1).reshape(c * 9, H * Wd)
    return (w.reshape(o, c * 9) @ cols).reshape(o, H, Wd) + b[:, None, None]


def _np_lsm(z):
    z = z - z.max(-1, keepdims=True)
    return z - np.log(np.exp(z).sum(-1, keepdims=True))


def _np_sig(x):
    return 1.0 / (1.0 + np.exp(-x))


class _NpOne:
    """numpy mirror of train3.Net inference (see agent3._One for the torch version and the interface)."""
    def __init__(self, blob, cfg, team=None):
        d = np.load(io.BytesIO(zlib.decompress(base64.b85decode(blob))))
        self.W = {k: d[k].astype(np.float32) for k in d.files}; self.cfg = cfg; self.tv = _team_vec(cfg, team)
        self.nb = cfg["blocks"]; self.ch = cfg["ch"]

    def _lin(self, name, x):
        return x @ self.W[name + ".weight"].T + self.W[name + ".bias"]

    def encode(self, B, G):
        G = _with_team(G, self.tv)
        W = self.W; x = np.concatenate([B[0], np.broadcast_to(G[0][:, None, None], (G.shape[1], 10, 10))], 0).astype(np.float32)
        h = np.maximum(_np_conv3(x, W["inp.weight"], W["inp.bias"]), 0)
        for k in range(self.nb):
            a = np.maximum(_np_conv3(h, W[f"body.{k}.a.weight"], W[f"body.{k}.a.bias"]), 0)
            h = np.maximum(h + _np_conv3(a, W[f"body.{k}.b.weight"], W[f"body.{k}.b.bias"]), 0)
        return h

    def units(self, h, G, ux, uy, uv):
        G = _with_team(G, self.tv); n = len(ux)
        z0 = np.concatenate([h[:, uy, ux].T, uv, np.repeat(G, n, 0)], 1)
        z = np.maximum(self._lin("unit.2", np.maximum(self._lin("unit.0", z0), 0)), 0)
        opl = _np_lsm(self._lin("u_op", z))
        q = self._lin("tq.2", np.maximum(self._lin("tq.0", z0), 0))
        tl = _np_lsm(q @ h.reshape(h.shape[0], -1) / np.sqrt(h.shape[0]))
        return opl, tl, z

    def qty(self, z, i, cls):
        oh = np.zeros(self.W["u_op.weight"].shape[0], np.float32); oh[cls] = 1
        return _np_lsm(self._lin("u_q", np.concatenate([z[i], oh])))

    def m_start(self, h, G, MS):
        G = _with_team(G, self.tv)
        pooled = np.concatenate([h.mean((1, 2)), h.max((1, 2)), G[0], MS[0]])
        ctx = np.tanh(self._lin("m_ctx.2", np.maximum(self._lin("m_ctx.0", pooled), 0)))
        return (ctx, ctx)

    def m_step(self, st, prev_t, prev_q, sl):
        W = self.W; state, ctx = st
        x = np.concatenate([W["m_tok_emb.weight"][prev_t], W["m_q_emb.weight"][prev_q], W["m_slot_emb.weight"][sl], ctx])
        gi = W["m_gru.weight_ih"] @ x + W["m_gru.bias_ih"]; gh = W["m_gru.weight_hh"] @ state + W["m_gru.bias_hh"]
        H = state.shape[0]
        r = _np_sig(gi[:H] + gh[:H]); z = _np_sig(gi[H:2 * H] + gh[H:2 * H]); nn_ = np.tanh(gi[2 * H:] + r * gh[2 * H:])
        state = (1 - z) * nn_ + z * state
        return (state, ctx), _np_lsm(self._lin("m_tok", state))

    def m_qty(self, st, tok):
        x = np.concatenate([st[0], self.W["m_tok_emb.weight"][tok]])
        return _np_lsm(self._lin("m_q.2", np.maximum(self._lin("m_q.0", x), 0)))


def _make_model(ckpt=None, team=None):
    ms = [_NpOne(b, c, team) for b, c in zip(_BLOBS, _CFGS)]
    return ms[0] if len(ms) == 1 else _Ens(ms)
'''


def ckpt_blob(path, dtype=np.float16):
    import torch
    ck = torch.load(path, map_location="cpu", weights_only=False)
    sd = {k: v.numpy().astype(np.float32) for k, v in ck["state"].items()}
    cfg = dict(ck["cfg"]); cfg.setdefault("u_dim", 34); cfg.setdefault("uext", ["motion"] if cfg["u_dim"] > 34 else [])
    cfg.setdefault("teams", [])
    # checkpoints from before the shed-after-units market input: zero-pad (same as agent3._One)
    import feat3 as F
    g_dim = cfg.get("g_dim") or F.G_DIM
    need = 2 * cfg["ch"] + g_dim + F.MS_DIM
    w = sd["m_ctx.0.weight"]
    if w.shape[1] < need:
        sd["m_ctx.0.weight"] = np.concatenate([w, np.zeros((w.shape[0], need - w.shape[1]), np.float32)], 1)
    buf = io.BytesIO(); np.savez(buf, **{k: v.astype(dtype) for k, v in sd.items()})
    return base64.b85encode(zlib.compress(buf.getvalue(), 9)).decode(), cfg


def agent_regions():
    src = open(os.path.join(HERE, "agent3.py")).read()
    a0 = src.index("_MOVES = "); a1 = src.index("\nclass _One:")
    b0 = src.index("# ============================== BUNDLE START"); b1 = src.index("# ============================== BUNDLE END")
    return src[a0:a1], src[b0:b1]


def build(ckpts, flags, dtype=np.float16):
    sys.path.insert(0, HERE)
    blobs, cfgs = zip(*[ckpt_blob(c, dtype) for c in ckpts])
    feat_src = open(FEAT_PY).read(); feat3_src = open(os.path.join(HERE, "feat3.py")).read()
    helpers, agent_code = agent_regions()
    b64 = lambda s: base64.b64encode(s.encode()).decode()
    head = f'''"""Kaggriculture BC v3 agent (numpy only, self-contained). Generated by lab/pavel/bc3/export3.py.
Models: {len(ckpts)}; flags: {json.dumps(flags)}."""
import base64, io, os, sys, types, zlib
import numpy as np

def _load_module(name, src_b64, extra=None):
    m = types.ModuleType(name); m.__dict__["__file__"] = "/nonexistent/" + name + ".py"
    m.__dict__.update(extra or {{}})
    exec(compile(base64.b64decode(src_b64).decode(), name + ".py", "exec"), m.__dict__)
    sys.modules[name] = m
    return m

_load_module("feat", {b64(feat_src)!r})
F = _load_module("feat3", {b64(feat3_src)!r})
_BLOBS = {list(blobs)!r}
_CFGS = {list(cfgs)!r}
'''
    tail = f'''
_AG = Agent(None, **{flags!r})


def agent(obs, config=None):
    try:
        return _AG(obs, config)
    except Exception:
        return {{"farmer": ["PASS"], "hands": [], "market": []}}
'''
    return head + NP_MODEL + "\n" + helpers + "\n" + agent_code + "\n" + tail


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ckpt", required=True); ap.add_argument("--out", required=True)
    for f in ("fill", "smask", "notrip", "persist", "trustop", "msample", "sample"):
        ap.add_argument("--" + f, action="store_true")
    ap.add_argument("--team", default=None); ap.add_argument("--fp32", action="store_true", help="float32 weights (2x size)")
    a = ap.parse_args()
    flags = {f: True for f in ("fill", "smask", "notrip", "persist", "trustop", "msample", "sample") if getattr(a, f)}
    if a.team:
        flags["team"] = a.team
    src = build([c for c in a.ckpt.split(",") if c], flags, np.float32 if a.fp32 else np.float16)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w").write(src); print("wrote", a.out, f"{len(src) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
