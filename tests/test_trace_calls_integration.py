"""Integration tests for ProjectSearch.trace_calls with real cross-file references."""

import tempfile
import unittest
from pathlib import Path

from code_context.search import ProjectSearch


class TestTraceCallsIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        (self.project / "definitions.py").write_text(
            "class Calculator:\n"
            "    def add(self, a, b):\n"
            "        return a + b\n"
            "    def multiply(self, a, b):\n"
            "        return a * b\n"
        )
        (self.project / "usage.py").write_text(
            "from definitions import Calculator\n"
            "calc = Calculator()\n"
            "result = calc.add(1, 2)\n"
            "other = calc.add(result, 3)\n"
        )
        self.search = ProjectSearch(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_cross_file_calls(self):
        results = self.search.trace_calls("Calculator.add")
        self.assertGreater(len(results), 0)
        found_usage = any("usage.py" in r["file"] for r in results)
        self.assertTrue(found_usage, f"Expected usage.py in results: {results}")

    def test_finds_all_call_sites(self):
        results = self.search.trace_calls("Calculator.add")
        # There are two calls to calc.add in usage.py
        usage_calls = [r for r in results if "usage.py" in r["file"]]
        self.assertEqual(len(usage_calls), 2)

    def test_no_results_for_undefined_symbol(self):
        results = self.search.trace_calls("UndefinedFunction")
        self.assertEqual(results, [])

    def test_dotted_symbol_with_multiple_files(self):
        (self.project / "advanced.py").write_text("from definitions import *  # noqa: F403\ncalc = Calculator()\ncalc.multiply(5, 6)\n")
        results = self.search.trace_calls("Calculator.multiply")
        self.assertGreater(len(results), 0)
