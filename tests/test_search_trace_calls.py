"""Unit tests for ProjectSearch.trace_calls behavior."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from search import ProjectSearch


class TestTraceCalls(unittest.TestCase):
    def test_trace_calls_supports_dotted_symbol_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "router.py").write_text("class LLMRouter:\n    def generate(self):\n        pass\n")
            (project / "consumer.py").write_text("self._router.generate(prompt=\"x\")\n")

            search = ProjectSearch(project)
            with patch.object(
                search,
                "find_symbols",
                return_value=[{"file": "router.py", "name": "generate", "line": 2, "type": "method"}],
            ):
                results = search.trace_calls("LLMRouter.generate")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["file"], "consumer.py")
            self.assertEqual(results[0]["line"], 1)

    def test_trace_calls_still_searches_without_definitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "service.py").write_text("handler.login(user)\n")

            search = ProjectSearch(project)
            with patch.object(search, "find_symbols", return_value=[]):
                results = search.trace_calls("login")

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["file"], "service.py")
