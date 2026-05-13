"""Unit tests for ProjectSearch.dir_summary (ls -la replacement)."""

import tempfile
import unittest
from pathlib import Path

from code_context.search import ProjectSearch


class TestDirSummary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        (self.project / "main.py").write_text("x = 1\n")
        (self.project / "utils.py").write_text("y = 2\n")
        (self.project / "data").mkdir()
        (self.project / "data" / "config.json").write_text("{}")
        (self.project / "data" / "nested").mkdir()
        (self.project / "data" / "nested" / "deep.txt").write_text("deep")
        self.search = ProjectSearch(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def test_basic_summary_contains_project_name(self):
        result = self.search.dir_summary()
        self.assertIn(self.project.name, result)
        self.assertIn(".py: 2 files", result)

    def test_depth_1_hides_nested_files(self):
        result = self.search.dir_summary(depth=1)
        self.assertIn("data", result)
        # depth=1 should not recurse into subdirs, so nested shouldn't appear
        self.assertNotIn("deep.txt", result)

    def test_error_for_nonexistent_directory(self):
        result = self.search.dir_summary(dir_path="nonexistent")
        self.assertIn("Error", result)
