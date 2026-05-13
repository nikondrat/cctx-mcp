"""Unit tests for ProjectSearch.get_dependencies."""

import tempfile
import unittest
from pathlib import Path

from code_context.search import ProjectSearch


def _ts_available() -> bool:
    try:
        from analyzers.typescript import TypeScriptAnalyzer
        _ = TypeScriptAnalyzer()
        return True
    except Exception:
        return False


class TestDependenciesPython(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        self.search = ProjectSearch(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def test_python_imports_are_detected(self):
        f = self.project / "mod.py"
        f.write_text("import os\nfrom pathlib import Path\n")
        deps = self.search.get_dependencies(f)
        self.assertIsNotNone(deps)
        self.assertIn("os", deps)
        self.assertIn("pathlib", deps)

    def test_no_imports_returns_empty_list(self):
        f = self.project / "mod.py"
        f.write_text("x = 1\n")
        deps = self.search.get_dependencies(f)
        self.assertEqual(deps, [])

    def test_nonexistent_file_returns_none(self):
        deps = self.search.get_dependencies(self.project / "nonexistent.py")
        self.assertIsNone(deps)

    @unittest.skipIf(not _ts_available(), "TypeScript analyzer not available")
    def test_typescript_imports(self):
        f = self.project / "app.ts"
        f.write_text('import { Component } from "@angular/core";\n')
        deps = self.search.get_dependencies(f)
        self.assertIsNotNone(deps)
        self.assertIn("@angular/core", deps)
