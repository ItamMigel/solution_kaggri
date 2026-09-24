"""Extract per-player action tapes from replays. tape[k] = action the agent returned at observation step k (k=0..718).
Also the shop order seen at step 144 (first two shops pick the route in the yhay/Horizon family)."""
import gzip, json

def load(path):
    with (gzip.open if path.endswith(".gz") else open)(path, "rt") as f:
        return json.load(f)

def tapes_of(d):
    steps = d["steps"]; names = d["info"].get("TeamNames", ["p0", "p1"])
    out = []
    for p in range(2):
        tape = [steps[k + 1][p]["action"] for k in range(len(steps) - 1)]
        obs144 = steps[144][0]["observation"] if len(steps) > 144 else {}
        shops = list((obs144.get("town") or {}).get("unlocked_shops") or [])
        out.append({"name": names[p], "player": p, "reward": d["rewards"][p], "opp_reward": d["rewards"][1 - p],
                    "shops144": shops, "tape": tape})
    return out
