from __future__ import annotations

import pathlib
import tempfile
import unittest

from lab.hplus.fertilizer_hand import DEFAULT, build, normalise


BASE = pathlib.Path("/workspace/shared/candidates/es1_g9/pkg/main.py")


class FertilizerHandBuildTest(unittest.TestCase):
    def test_builds_default_and_enabled_agents(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            default = pathlib.Path(td) / "default.py"
            enabled = pathlib.Path(td) / "enabled.py"
            self.assertTrue(build(BASE, {}, default)["default_off"])
            self.assertFalse(build(BASE, {"fh_on": True}, enabled)["default_off"])
            self.assertIn("_FH_PARENT = agent", default.read_text())
            compile(enabled.read_text(), str(enabled), "exec")

    def test_rejects_unsafe_gene_shapes(self) -> None:
        with self.assertRaises(ValueError):
            normalise({"fh_day0": 21, "fh_day1": 20})
        with self.assertRaises(ValueError):
            normalise({"fh_take": 0})
        with self.assertRaises(ValueError):
            normalise({"fh_crops": ["WHEAT"]})
        with self.assertRaises(ValueError):
            normalise({"fh_reserve": -1})
        with self.assertRaises(ValueError):
            normalise({"fh_max_hires_today": 31})


if __name__ == "__main__":
    unittest.main()
