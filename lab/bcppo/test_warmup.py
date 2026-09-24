"""Regression check: critic warm-up may not alter any BC policy parameter."""
from __future__ import annotations

import unittest

import torch

from lab.bcppo import policy
from lab.bcppo.ppo import _set_value_warmup_trainable


class ValueWarmupTest(unittest.TestCase):
    def test_only_value_head_has_gradients_in_warmup(self) -> None:
        net = policy.PolicyNet(gdim=7, ch=8, blocks=1)
        _set_value_warmup_trainable(net, True)
        self.assertTrue(all(p.requires_grad for name, p in net.named_parameters() if name.startswith("value.")))
        self.assertTrue(all(not p.requires_grad for name, p in net.named_parameters() if not name.startswith("value.")))
        frozen_before = {name: p.detach().clone() for name, p in net.named_parameters() if not name.startswith("value.")}
        opt = torch.optim.Adam(net.parameters(), lr=1e-3)
        # ``value`` receives pooled trunk features in PPO.  Its own update must
        # work while every action-producing parameter stays byte-identical.
        net.value(torch.randn(4, 2 * 8 + 7)).square().mean().backward()
        opt.step()
        for name, before in frozen_before.items():
            self.assertTrue(torch.equal(before, dict(net.named_parameters())[name]))
        _set_value_warmup_trainable(net, False)
        self.assertTrue(all(p.requires_grad for _, p in net.named_parameters()))


if __name__ == "__main__":
    unittest.main()
