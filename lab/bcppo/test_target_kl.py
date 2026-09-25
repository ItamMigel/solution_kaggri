"""CPU regressions for PPO's rollout-policy KL guard."""
from __future__ import annotations

import unittest

import torch

from lab.bcppo.ppo import _nonnegative_approx_kl


class TargetKlTest(unittest.TestCase):
    def test_identical_policies_have_zero_estimate(self) -> None:
        self.assertEqual(_nonnegative_approx_kl(torch.zeros(32)).item(), 0.0)

    def test_estimate_cannot_be_negative(self) -> None:
        # The old E[old_logp - new_logp] diagnostic can be negative on a
        # minibatch.  This form is convex sample-by-sample and drives stopping.
        log_ratio = torch.tensor([-4.0, -0.3, 0.2, 2.0])
        self.assertGreater(_nonnegative_approx_kl(log_ratio).item(), 0.0)


if __name__ == "__main__":
    unittest.main()
