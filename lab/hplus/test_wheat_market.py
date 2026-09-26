from pathlib import Path
import unittest

from wheat_market import build


class WheatMarketBuildTest(unittest.TestCase):
    def test_default_off_and_on_compile(self):
        base = Path("/workspace/shared/candidates/es6_c4g15/pkg/main.py")
        out = Path("/tmp/t031_wheat_market_test.py")
        try:
            self.assertTrue(build(base, {}, out)["default_off"])
            self.assertFalse(build(base, {"wm_on": True}, out)["default_off"])
        finally:
            out.unlink(missing_ok=True)
            out.with_suffix(".py.wheat_market.json").unlink(missing_ok=True)


if __name__ == "__main__": unittest.main()
