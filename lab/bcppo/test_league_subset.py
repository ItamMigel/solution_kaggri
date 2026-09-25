"""The league subset fast path must preserve deterministic opponent actions."""
from __future__ import annotations

import unittest

import torch

from lab.bcppo import gpufeat, policy
from lab.bcppo.ppo import _league_subset_actions, _merge_actions
from lab.gpuenv.env import VecKaggriculture


class LeagueSubsetTest(unittest.TestCase):
    def test_greedy_subset_actions_match_full_batch(self) -> None:
        batch = 4
        dev = "cpu"
        ve = VecKaggriculture(batch, device=dev, cuda_graph=False)
        state = ve.reset(torch.arange(100, 100 + batch))
        order = gpufeat.ShopOrder(batch, dev)
        order.update(state)
        _, glob, *_ = gpufeat.features(state, 1, order)
        team = torch.tensor([[1.0, 0.0, 0.0]])
        nets = [policy.PolicyNet(glob.shape[1] + team.shape[1], ch=8, blocks=1).eval()
                for _ in range(2)]
        league = {f"opponent{i}": (net, .5, team) for i, net in enumerate(nets)}
        names = list(league)
        labels = torch.tensor([0, 1, 0, 1])
        full = {name: policy.act(league[name][0], state, 1, order, league[name][2], greedy=True)
                for name in names}
        expected = _merge_actions(full, labels, names)
        actual = _league_subset_actions(league, state, order, labels, names, greedy=True)
        for got, want in zip(actual, expected):
            self.assertTrue(torch.equal(got, want))


if __name__ == "__main__":
    unittest.main()
