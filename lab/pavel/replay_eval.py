"""Evaluate candidate agents in the recorded worlds of real Kaggle episodes ("replay eval").

For every (recorded episode, candidate):
  * the world is rebuilt exactly (recorded seed + configuration, official kaggle_environments engine);
  * the candidate plays the EXPERT team's seat;
  * the other seat replays its recorded action tape open-loop (it does not react to the candidate).
Built-in candidate "expert" = the expert's own recorded tape: it must reproduce the recorded rewards exactly
(sanity check + baseline row). It is always included unless --no-expert.

Candidates are loaded like Kaggle / solution/game_worker.py do: the main.py PATH is given to kaggle_environments
(build_agent -> get_last_callable on the file source, the agent folder is on sys.path while the file executes),
cwd = agent folder during load and the whole game, one fresh Python process per game (no state leaks between
games), policy RNG seeded like game_worker.py. Agent stdout/stderr is swallowed; exceptions, None / non-dict
returns and ERROR/INVALID/TIMEOUT steps are counted. The replay's actTimeout/overage limits stay in force.

usage (from this folder):
  python replay_eval.py --glob '../../../replays/56521745/*.gz' --team Boey \
      --agent bc=../../../runs/some_agent/main.py --limit 20 --workers 8 --out ../../../runs/replay_eval/boey.jsonl [--days]
"""
import argparse
import concurrent.futures
import contextlib
import glob
import gzip
import io
import json
import math
import os
import re
import subprocess
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.abspath(__file__)
MARK = "@@REPLAY_EVAL_RESULT@@"
BAD_STATUS = ("ERROR", "INVALID", "TIMEOUT")
THREAD_ENV = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}


def _get(o, k, default=None):
    try:
        v = o.get(k, default)
    except AttributeError:
        v = getattr(o, k, default)
    return default if v is None else v


# ------------------------------------------------------------------ worker side (one game per process)
def _tape_agent(tape):
    """Open-loop replay of a recorded action tape: tape[k] is the action submitted at observation step k."""
    state = {"n": 0}

    def agent(obs, config=None):
        k = _get(obs, "step", None)
        k = state["n"] if k is None else int(k)
        state["n"] = k + 1
        act = tape[k] if 0 <= k < len(tape) else None
        return act or {}
    return agent


_TORCH_PINNED = [False]


def _pin_torch_threads():
    # OMP/MKL env vars already cap threads; additionally pin torch as soon as the agent has imported it
    # (importing torch eagerly would cost ~2 s per game for agents that do not use it).
    if not _TORCH_PINNED[0] and "torch" in sys.modules:
        _TORCH_PINNED[0] = True
        try:
            sys.modules["torch"].set_num_threads(1)
        except Exception:
            pass


def _file_agent(path, counters):
    """Exactly the kaggle_environments path loader (lazy get_last_callable on the file source), wrapped only to
    count exceptions and None / non-dict returns. Exceptions are re-raised so the engine handles them as usual."""
    from kaggle_environments.agent import build_agent
    inner, _ = build_agent(path, {}, "kaggriculture")

    def agent(obs, config):
        try:
            a = inner(obs, config)
        except BaseException:
            counters["exceptions"] += 1
            if counters["first_exception_step"] is None:
                counters["first_exception_step"] = _get(obs, "step")
            raise
        finally:
            _pin_torch_threads()
        if a is None:
            counters["none_actions"] += 1
        elif not isinstance(a, dict):
            counters["nondict_actions"] += 1
        return a
    return agent


def _load_replay(path):
    with (gzip.open(path, "rt", encoding="utf-8") if path.endswith(".gz") else open(path, encoding="utf-8")) as f:
        return json.load(f)


def _money(steps, t, seat):
    try:
        return float(steps[t][0]["observation"]["farms"][seat]["money"])
    except (IndexError, KeyError, TypeError):
        return None


def _run_game(job):
    import random
    import numpy as np
    from kaggle_environments import make

    rpath, team, cand = job["replay"], job["team"], job["candidate"]
    d = _load_replay(rpath)
    names = list(d["info"]["TeamNames"])
    base = dict(file=os.path.basename(rpath), episode=d["info"].get("EpisodeId"), team=team, candidate=cand)
    if team not in names:
        return dict(base, error="team_not_in_episode", teams=names)
    p = names.index(team)
    seed = d["info"]["seed"]
    nsteps = len(d["steps"])
    tapes = [[d["steps"][k + 1][s]["action"] for k in range(nsteps - 1)] for s in (0, 1)]
    cfg = {k: v for k, v in d["configuration"].items() if k not in ("agents", "seed")}
    cfg["seed"] = seed
    rec = list(d["rewards"])
    rec_status = list(d.get("statuses") or [])
    tpd = int(cfg.get("turnsPerDay", 24))
    day_idx = list(range(tpd - 1, int(cfg.get("episodeSteps", nsteps)), tpd))
    rec_days = [[_money(d["steps"], t, s) for t in day_idx] for s in (0, 1)] if job.get("days") else None
    del d  # the parsed replay is large; free it before the game

    base.update(expert_seat=p, opponent=names[1 - p], self_play=names.count(team) > 1, seed=seed,
                rec_expert=rec[p], rec_opp=rec[1 - p], rec_status=rec_status)
    counters = dict(exceptions=0, first_exception_step=None, none_actions=0, nondict_actions=0)
    if job.get("path"):
        os.chdir(os.path.dirname(job["path"]))
        cand_agent = _file_agent(job["path"], counters)
    else:
        cand_agent = _tape_agent(tapes[p])
    agents = [None, None]
    agents[p] = cand_agent
    agents[1 - p] = _tape_agent(tapes[1 - p])

    policy_seed = (int(seed) ^ 0x6D2B79F5) % 2 ** 32  # same policy RNG stream as solution/game_worker.py
    random.seed(policy_seed)
    np.random.seed(policy_seed)
    t0 = time.perf_counter()
    env = make("kaggriculture", configuration=cfg, debug=False)
    env.run(agents)
    game_seconds = time.perf_counter() - t0

    status = [s.status for s in env.state]
    rewards = [s.reward for s in env.state]

    def bad_steps(seat):
        return [(t, pair[seat].status) for t, pair in enumerate(env.steps[1:], 1)
                if pair[seat].status in BAD_STATUS or not isinstance(pair[seat].action, dict)]
    inv, inv_opp = bad_steps(p), bad_steps(1 - p)
    inv_status = {}
    for _, st in inv:
        inv_status[st] = inv_status.get(st, 0) + 1
    durs = [pair[p]["duration"] for pair in env.logs if len(pair) > p and "duration" in pair[p]]

    sim_c, sim_o = rewards[p], rewards[1 - p]
    failed = bool(inv) or status[p] != "DONE" or sim_c is None
    margin = (sim_c - sim_o) if (sim_c is not None and sim_o is not None) else None
    win = 0.0 if (failed or margin is None) else (1.0 if margin > 0 else 0.5 if margin == 0 else 0.0)
    row = dict(base,
               sim_cand=sim_c, sim_opp=sim_o, margin=margin, win=win,
               rec_margin=rec[p] - rec[1 - p],
               delta_vs_rec=(sim_c - rec[p]) if sim_c is not None else None,
               status=status, status_cand=status[p], status_opp=status[1 - p], failed=failed,
               invalid_steps=len(inv), first_invalid_step=inv[0][0] if inv else None, invalid_by_status=inv_status,
               opp_invalid_steps=len(inv_opp), **counters,
               calls=len(durs), max_ms=round(1000 * max(durs, default=0.0), 1),
               overage_left=_get(env.state[p].observation, "remainingOverageTime"),
               n_steps=len(env.steps), game_seconds=round(game_seconds, 2))
    if sim_c is None:  # keep the money visible even when the engine nulls the reward
        row["sim_cand_money_last_obs"] = _money(env.steps, len(env.steps) - 1, p)
    if job.get("days"):
        row["day_steps"] = day_idx
        row["days_sim_cand"] = [_money(env.steps, t, p) for t in day_idx]
        row["days_sim_opp"] = [_money(env.steps, t, 1 - p) for t in day_idx]
        row["days_rec_expert"] = rec_days[p]
        row["days_rec_opp"] = rec_days[1 - p]
    return row


def _worker_main():
    job = json.loads(sys.stdin.read())
    # The agent is an importable folder, this lab folder is not (Kaggle does not have it on sys.path).
    sys.path[:] = [q for q in sys.path if os.path.abspath(q or ".") != HERE]
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            res = _run_game(job)
    except BaseException:
        res = dict(file=os.path.basename(job["replay"]), team=job["team"], candidate=job["candidate"],
                   error="worker_exception", detail=traceback.format_exc()[-4000:])
    if "error" in res:
        res["process_output"] = captured.getvalue()[-2000:]
    sys.__stdout__.write(MARK + json.dumps(res) + "\n")
    sys.__stdout__.flush()
    os._exit(0)  # do not wait for stray agent threads / atexit hooks


# ------------------------------------------------------------------ parent side
def run_job(job, timeout):
    t0 = time.perf_counter()
    base = dict(file=os.path.basename(job["replay"]), team=job["team"], candidate=job["candidate"])
    cwd = os.path.dirname(job["path"]) if job.get("path") else HERE
    env = dict(os.environ, **THREAD_ENV)
    try:
        proc = subprocess.run([sys.executable, SCRIPT, "--_worker"], input=json.dumps(job), capture_output=True,
                              encoding="utf-8", errors="replace", timeout=timeout, cwd=cwd, env=env)
    except subprocess.TimeoutExpired:
        return dict(base, error="wall_timeout", timeout_seconds=timeout, seconds=round(time.perf_counter() - t0, 1))
    lines = [ln for ln in (proc.stdout or "").splitlines() if ln.startswith(MARK)]
    if not lines:
        return dict(base, error="worker_process_failed", returncode=proc.returncode,
                    detail=((proc.stderr or "") + (proc.stdout or ""))[-4000:],
                    seconds=round(time.perf_counter() - t0, 1))
    res = json.loads(lines[-1][len(MARK):])
    res["seconds"] = round(time.perf_counter() - t0, 2)
    return res


def parse_agent(value):
    if "=" not in value:
        raise SystemExit(f"--agent expects NAME=PATH, got {value!r}")
    name, path = value.split("=", 1)
    if not name or not all(c.isalnum() or c in "_-." for c in name):
        raise SystemExit(f"bad agent name {name!r}")
    if name == "expert":
        raise SystemExit("'expert' is the built-in recorded-tape candidate; pick another name")
    path = os.path.abspath(os.path.expanduser(path))
    if os.path.isdir(path):
        path = os.path.join(path, "main.py")
    if not os.path.isfile(path) or not path.endswith(".py"):
        raise SystemExit(f"agent file not found: {path}")
    return name, path


_TEAMS_RE = re.compile(r'"TeamNames"\s*:\s*(\[[^\]]*\])')


def team_names(path):
    """Cheap scan for info.TeamNames (keys are sorted, "info" precedes the big "steps" array)."""
    opener = gzip.open if path.endswith(".gz") else open
    buf = ""
    with opener(path, "rt", encoding="utf-8") as f:
        while True:
            chunk = f.read(1 << 16)
            buf += chunk
            m = _TEAMS_RE.search(buf)
            if m:
                return json.loads(m.group(1))
            if not chunk or len(buf) > (8 << 20):
                break
    return list(_load_replay(path)["info"]["TeamNames"])


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def _se(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return float("nan")
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1) / len(xs))


def summarize(rows, order):
    hdr = (f"{'candidate':<16} {'n':>4} {'err':>4} {'fail':>4} {'win%':>6} {'cand$':>10} {'opp$':>10} "
           f"{'margin':>10} {'±se':>8} {'cand-rec':>10} {'invalid':>7} {'exc':>5} {'none':>5} {'exact':>5} {'sec':>6}")
    print(hdr)
    print("-" * len(hdr))
    # recorded baseline over the episodes that ran
    eps = {}
    for r in rows:
        if "error" not in r:
            eps[r["episode"]] = r
    if eps:
        rr = list(eps.values())
        rw = [1.0 if r["rec_margin"] > 0 else 0.5 if r["rec_margin"] == 0 else 0.0 for r in rr]
        print(f"{'(recorded)':<16} {len(rr):>4} {'':>4} {'':>4} {100 * _mean(rw):>6.1f} "
              f"{_mean([r['rec_expert'] for r in rr]):>10.0f} {_mean([r['rec_opp'] for r in rr]):>10.0f} "
              f"{_mean([r['rec_margin'] for r in rr]):>10.0f} {_se([r['rec_margin'] for r in rr]):>8.0f}")
    for cand in order:
        rs = [r for r in rows if r.get("candidate") == cand]
        ok = [r for r in rs if "error" not in r]
        if not rs:
            continue
        exact = sum(1 for r in ok if r["sim_cand"] == r["rec_expert"] and r["sim_opp"] == r["rec_opp"])
        print(f"{cand:<16} {len(ok):>4} {len(rs) - len(ok):>4} {sum(r['failed'] for r in ok):>4} "
              f"{100 * _mean([r['win'] for r in ok]):>6.1f} {_mean([r['sim_cand'] for r in ok]):>10.0f} "
              f"{_mean([r['sim_opp'] for r in ok]):>10.0f} {_mean([r['margin'] for r in ok]):>10.0f} "
              f"{_se([r['margin'] for r in ok]):>8.0f} {_mean([r['delta_vs_rec'] for r in ok]):>10.0f} "
              f"{sum(r['invalid_steps'] for r in ok):>7} {sum(r['exceptions'] for r in ok):>5} "
              f"{sum(r['none_actions'] + r['nondict_actions'] for r in ok):>5} {exact:>5} "
              f"{_mean([r.get('seconds') for r in ok]):>6.0f}")
    print("columns: fail = games with any ERROR/INVALID/TIMEOUT step (scored as loss); invalid = such steps; "
          "exc = agent exceptions; none = None/non-dict returns; exact = games with sim == recorded for both "
          "seats; cand-rec = sim candidate money - recorded expert money; sec = mean wall seconds per game")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", action="append", default=[], metavar="NAME=PATH/main.py",
                    help="candidate agent (repeatable); PATH may be a folder containing main.py")
    ap.add_argument("--glob", required=True, help="recorded replays, e.g. 'replays/56521745/*.gz'")
    ap.add_argument("--team", required=True, help="expert team name (its seat is taken over by the candidate)")
    ap.add_argument("--limit", type=int, default=0, help="first N matching episodes (sorted by file name)")
    ap.add_argument("--out", required=True, help="output JSONL, one row per (episode, candidate); overwritten")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--days", action="store_true", help="also record end-of-day money (sim and recorded)")
    ap.add_argument("--no-expert", action="store_true", help="skip the built-in 'expert' tape candidate")
    ap.add_argument("--skip-self-play", action="store_true",
                    help="skip episodes where the expert team is in both seats (e.g. the seed-0 validation game)")
    ap.add_argument("--game-timeout", type=float, default=1800.0, help="hard wall limit per game process, s")
    a = ap.parse_args()

    cands = [] if a.no_expert else [("expert", None)]
    for v in a.agent:
        cands.append(parse_agent(v))
    if len({n for n, _ in cands}) != len(cands):
        raise SystemExit("duplicate candidate names")
    if not cands:
        raise SystemExit("nothing to evaluate")

    files = []
    for f in sorted(glob.glob(a.glob)):
        if not (f.endswith(".json") or f.endswith(".json.gz")):
            continue
        try:
            names = team_names(f)
        except Exception as exc:
            print(f"skip unreadable {f}: {exc!r}", flush=True)
            continue
        if a.team in names and not (a.skip_self_play and names.count(a.team) > 1):
            files.append(f)
            if a.limit and len(files) >= a.limit:
                break
    if not files:
        raise SystemExit(f"no replays matching {a.glob!r} contain team {a.team!r}")

    jobs = [dict(replay=os.path.abspath(f), team=a.team, candidate=n, path=pth, days=a.days)
            for f in files for n, pth in cands]
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(f"{len(files)} episodes x {len(cands)} candidates = {len(jobs)} games, workers={a.workers} -> {out}",
          flush=True)
    rows = []
    every = max(1, len(jobs) // 20)
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, a.workers)) as pool, open(out, "w") as fo:
        futs = [pool.submit(run_job, j, a.game_timeout) for j in jobs]
        for i, fut in enumerate(concurrent.futures.as_completed(futs), 1):
            r = fut.result()
            rows.append(r)
            fo.write(json.dumps(r) + "\n")
            fo.flush()
            if "error" in r:
                print(f"[{i}/{len(jobs)}] ERROR {r.get('file')} {r.get('candidate')}: {r['error']} "
                      f"{(r.get('detail') or '')[-300:]}", flush=True)
            elif i % every == 0 or i == len(jobs):
                print(f"[{i}/{len(jobs)}] ep {r['episode']} {r['candidate']}: {r['sim_cand']:.0f} vs {r['sim_opp']:.0f} "
                      f"(rec {r['rec_expert']:.0f} vs {r['rec_opp']:.0f}) {r['seconds']:.0f}s "
                      f"elapsed {time.perf_counter() - t0:.0f}s", flush=True)
    print()
    summarize(rows, [n for n, _ in cands])
    bad_expert = [r for r in rows if r.get("candidate") == "expert" and "error" not in r
                  and (r["sim_cand"] != r["rec_expert"] or r["sim_opp"] != r["rec_opp"])]
    if bad_expert:
        print(f"WARNING: expert tape did not reproduce the recording in {len(bad_expert)} games: "
              + ", ".join(str(r["episode"]) for r in bad_expert[:10]))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--_worker":
        _worker_main()
    else:
        main()
