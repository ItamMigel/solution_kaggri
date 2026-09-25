from __future__ import annotations

import pathlib
import tempfile
import unittest

from lab.hplus.tape_safe import build, normalise

BASE = pathlib.Path('/workspace/shared/candidates/es2_c1/pkg/main.py')


class TapeSafeBuildTest(unittest.TestCase):
    def test_build_after_es2_without_hp_rebinding(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / 'agent.py'
            info = build(BASE, {'ts_on': True, 'ts_ops': ['FEED']}, out)
            self.assertFalse(info['default_off'])
            text = out.read_text()
            self.assertIn('_TS_PARENT = agent', text)
            self.assertIn('_HP_BASE_AGENT = agent', text)
            compile(text, str(out), 'exec')

    def test_rejects_bad_genes(self) -> None:
        with self.assertRaises(ValueError):
            normalise({'ts_ops': ['DIG']})
        with self.assertRaises(ValueError):
            normalise({'ts_day0': 9, 'ts_day1': 8})


if __name__ == '__main__':
    unittest.main()
