from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lab.hplus.goose_microplan import build, normalise


BASE = Path("/workspace/shared/candidates/es5_c3g15/pkg/main.py")


class GooseMicroplanBuildTest(unittest.TestCase):
    def test_builds_default_and_enabled_agents(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            default = Path(td) / "default.py"
            enabled = Path(td) / "enabled.py"
            self.assertTrue(build(BASE, {}, default)["default_off"])
            self.assertFalse(build(BASE, {"g1_on": True}, enabled)["default_off"])
            self.assertIn("_G1_PARENT = agent", enabled.read_text())
            compile(enabled.read_text(), str(enabled), "exec")

    def test_rejects_unsupported_targets_or_typoes(self) -> None:
        with self.assertRaises(ValueError):
            normalise({"g1_target": 4})
        with self.assertRaises(ValueError):
            normalise({"goose_target": 4})


if __name__ == "__main__":
    unittest.main()
