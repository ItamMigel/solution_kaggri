"""Launch the legacy residual-PPO probe under the exact 1.32.7 economy.

Usage requires the temporary ``src.rl`` compatibility namespace described in
T010's run log.  The resulting checkpoint is research evidence only: promotion
also requires action equivalence with the deployed Horizon executor and a
paired external-opponent gate.
"""
from __future__ import annotations

from .runtime_1327 import apply


def main() -> int:
    apply()
    from src.rl import train_real

    # The old exploratory box allowed 20 hands, 18 cows and 16 sheep.  On the
    # 1.32.7 exact environment those tail samples can make a rollout several
    # times slower, while T011's top-replay census puts the useful frontier at
    # about 10 hands, 9--10 cows, 5--8 sheep and 4--6 geese.  Keep a little
    # headroom but exclude the unproductive, expensive tail before PPO sees it.
    caps = {"target_hands": 14, "n_cows": 12, "n_sheep": 10, "n_geese": 6}
    train_real.C.SPEC = tuple(
        (name, lo, min(hi, caps.get(name, hi)), integer)
        for name, lo, hi, integer in train_real.C.SPEC
    )

    # The ladder census makes geese a live portfolio decision.  The old
    # sensitivity table marked it dead only because its default sigma rounded
    # away from an integer target.
    if "n_geese" in train_real.DEAD:
        train_real.DEAD.remove("n_geese")
    return train_real.main()


if __name__ == "__main__":
    raise SystemExit(main())
