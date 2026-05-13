"""Unit tests for ProjectSearch.find_files (find replacement)."""

import tempfile
import unittest
from pathlib import Path

from code_context.search import ProjectSearch


class TestFindFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        (self.project / "main.py").write_text("x = 1\n")
        (self.project / "utils.py").write_text("y = 2\n")
        (self.project / "styles.css").write_text("body {}\n")
        (self.project / "sub").mkdir()
        (self.project / "sub" / "helper.ts").write_text("const a = 1;\n")
        self.search = ProjectSearch(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def test_extension_filter(self):
        results = self.search.find_files(extension="py")
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertTrue(r["path"].endswith(".py"))

    def test_name_pattern(self):
        results = self.search.find_files(name_pattern="*main*")
        self.assertEqual(len(results), 1)
        self.assertIn("main.py", results[0]["path"])

    def test_path_contains(self):
        results = self.search.find_files(path_contains="sub")
        self.assertEqual(len(results), 1)
        self.assertIn("helper.ts", results[0]["path"])

    def test_max_depth(self):
        results = self.search.find_files(max_depth=0)
        for r in results:
            self.assertNotIn("sub", r["path"])

    def test_no_results(self):
        results = self.search.find_files(extension="rs")
        self.assertEqual(results, [])
