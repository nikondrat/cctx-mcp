"""Unit tests for ProjectSearch.code_search (grep replacement)."""

import tempfile
import unittest
from pathlib import Path

from code_context.search import ProjectSearch


class TestCodeSearch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        (self.project / "greeter.py").write_text("def greet(name):\n    return f'hello {name}'\n")
        (self.project / "auth.py").write_text("def login(user):\n    return True\n")
        self.search = ProjectSearch(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def test_basic_text_search_finds_matches(self):
        results = self.search.code_search("def")
        self.assertGreater(len(results), 0)
        files = [r["file"] for r in results]
        self.assertIn("auth.py", files)

    def test_empty_results_when_no_match(self):
        results = self.search.code_search("zzz_nonexistent_zzz")
        self.assertEqual(results, [])

    def test_regex_mode(self):
        results = self.search.code_search(r"def\s+\w+", use_regex=True)
        self.assertGreater(len(results), 0)

    def test_invalid_regex_returns_error(self):
        results = self.search.code_search(r"[invalid", use_regex=True)
        self.assertTrue(any("error" in r for r in results))

    def test_file_pattern_filters_by_extension(self):
        results = self.search.code_search("def", file_pattern="*.py")
        self.assertGreater(len(results), 0)
        for r in results:
            self.assertTrue(r["file"].endswith(".py"))

    def test_case_sensitive_search(self):
        (self.project / "case_test.py").write_text("FOO\nfoo\nFoo\n")
        all_results = self.search.code_search("FOO", case_sensitive=True)
        self.assertGreater(len(all_results), 0)
        for r in all_results:
            self.assertIn("FOO", r["text"])
