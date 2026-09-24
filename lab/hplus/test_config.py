"""Regression tests for source-level M4 anchors and frozen-fold safety."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from lab.hplus.config import DEFAULT_GENES, BuildError, build, build_text, normalise
from lab.hplus.race import locked_fold


BASE = pathlib.Path("/workspace/shared/candidates/es1_g9/pkg/main.py")


class ConfigTest(unittest.TestCase):
    def test_genome_zero_is_byte_identical(self) -> None:
        source = BASE.read_text()
        got, genes = build_text(source, {})
        self.assertEqual(genes, DEFAULT_GENES)
        self.assertEqual(got.encode(), source.encode())
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / "main.py"
            info = build(BASE, {}, out)
            self.assertTrue(info["genome_zero_byte_identical"])
            self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(), hashlib.sha256(BASE.read_bytes()).hexdigest())

    def test_each_m4_anchor_changes_and_compiles(self) -> None:
        variants = [
            {"settings": {"budget_guard": True}},
            {"opening_qty": 9},
            {"router_switch_step": 660},
            {"fd_takeover_step": 704},
        ]
        source = BASE.read_text()
        for genes in variants:
            with self.subTest(genes=genes):
                got, _ = build_text(source, genes)
                self.assertNotEqual(got, source)
                compile(got, "m4.py", "exec")

    def test_rejects_unsafe_or_unknown_genes(self) -> None:
        with self.assertRaises(BuildError):
            normalise({"typo": True})
        with self.assertRaises(BuildError):
            normalise({"fd_takeover_step": 648})
        with self.assertRaises(BuildError):
            build_text(BASE.read_text(), {"settings": {"not_a_flag": True}})


class FoldTest(unittest.TestCase):
    def test_fold_is_stable_and_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "fold.json"
            first = locked_fold(path, name="capability", worlds=3, salt=123, excluded={1, 2, 3})
            second = locked_fold(path, name="capability", worlds=3, salt=123, excluded={1, 2, 3})
            self.assertEqual(first, second)
            self.assertFalse(set(first) & {1, 2, 3})
            with self.assertRaises(ValueError):
                locked_fold(path, name="race", worlds=3, salt=123, excluded=set())


class CompareCliTest(unittest.TestCase):
    def test_explicit_empty_builtin_panel_is_accepted(self) -> None:
        proc = subprocess.run(
            ["/workspace/solution_kaggri/.venv/bin/python", "compare.py", "--baselines", "--verify-only"],
            cwd="/workspace/wt/codex", text=True, capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
