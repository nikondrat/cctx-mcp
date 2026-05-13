"""Unit tests for analyze_project tool (inline os.walk logic)."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestAnalyzeProject(unittest.TestCase):
    def test_basic_project_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "mod.py").write_text("x = 1\n")
            (project / "utils.py").write_text("y = 2\n")
            (project / "data").mkdir()
            (project / "data" / "config.py").write_text("z = 3\n")

            from code_context.search import LANGUAGE_EXTENSIONS

            stats = {"files": 0, "languages": {}, "directories": 0}
            for root, dirs, files in project.walk():
                rel = Path(root).relative_to(project)
                if len(rel.parts) > 2:
                    dirs.clear()
                    continue
                stats["directories"] += 1
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "Pods", "build", "dist", ".git", "__pycache__", "venv", ".venv")]
                for file in files:
                    fp = Path(root) / file
                    ext = fp.suffix.lower()
                    if ext in LANGUAGE_EXTENSIONS:
                        stats["files"] += 1
                        lang = LANGUAGE_EXTENSIONS[ext].__name__.replace("Analyzer", "").lower()
                        stats["languages"][lang] = stats["languages"].get(lang, 0) + 1

            self.assertGreater(stats["files"], 0)
            self.assertIn("python", stats["languages"])
            self.assertEqual(stats["languages"]["python"], 3)

    def test_nonexistent_path_returns_error(self):
        from code_context.server import analyze_project
        result = analyze_project("/nonexistent/project")
        self.assertIn("Error", result)
