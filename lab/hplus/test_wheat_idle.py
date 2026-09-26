from pathlib import Path
import unittest

from wheat_idle import build


class WheatIdleBuildTest(unittest.TestCase):
    def test_default_off_and_on_compile(self):
        base = Path(__file__).resolve().parents[2] / "agents/horizon_v5_market.py"
        out = Path("/tmp/t030_wheat_idle_test.py")
        try:
            self.assertTrue(build(base, {}, out)["default_off"])
            self.assertFalse(build(base, {"wi_on": True}, out)["default_off"])
        finally:
            out.unlink(missing_ok=True)
            out.with_suffix(".py.wheat_idle.json").unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
