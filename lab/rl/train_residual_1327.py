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

    # The ladder census makes geese a live portfolio decision.  The old
    # sensitivity table marked it dead only because its default sigma rounded
    # away from an integer target.
    if "n_geese" in train_real.DEAD:
        train_real.DEAD.remove("n_geese")
    return train_real.main()


if __name__ == "__main__":
    raise SystemExit(main())
