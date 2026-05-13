"""Unit tests for CommitGenerator — Ollama calls mocked."""

import unittest
from unittest.mock import MagicMock, patch

from change_intel import ChangedFile, CompactChange
from commit_generator import CommitGenerator, CommitGeneratorConfig, _build_prompt, _sanitize, _looks_valid
from ollama_client import OllamaUnavailableError


def _make_cc(files, cues=None):
    change_types = sorted({f.change_type for f in files})
    total_add = sum(f.additions for f in files)
    total_del = sum(f.deletions for f in files)
    return CompactChange(
        files=files,
        change_count=len(files),
        total_additions=total_add,
        total_deletions=total_del,
        summary=f"{len(files)} file(s) changed",
        change_types=change_types,
        intent_cues=cues or [],
    )


class TestSanitize(unittest.TestCase):
    def test_strips_markdown_fence(self):
        raw = "```\nfeat: add thing\n```"
        self.assertEqual(_sanitize(raw), "feat: add thing")

    def test_strips_leading_bullet(self):
        self.assertEqual(_sanitize("- feat: fix bug"), "feat: fix bug")

    def test_truncates_to_72(self):
        long = "feat: " + "x" * 100
        self.assertLessEqual(len(_sanitize(long)), 72)

    def test_takes_first_nonempty_line(self):
        raw = "\n\nfeat: first line\nsome other text"
        self.assertEqual(_sanitize(raw), "feat: first line")


class TestLooksValid(unittest.TestCase):
    def test_valid_conventional(self):
        self.assertTrue(_looks_valid("feat(auth): add login"))
        self.assertTrue(_looks_valid("fix: handle null case"))
        self.assertTrue(_looks_valid("refactor!: rewrite parser"))

    def test_invalid_no_type(self):
        self.assertFalse(_looks_valid("Add login functionality"))
        self.assertFalse(_looks_valid(""))


class TestBuildPrompt(unittest.TestCase):
    def test_contains_file_paths(self):
        cc = _make_cc([ChangedFile("src/auth.py", "added", 20, 0)])
        prompt = _build_prompt(cc)
        self.assertIn("src/auth.py", prompt)

    def test_contains_intent_cues(self):
        cc = _make_cc([], cues=["includes test changes"])
        prompt = _build_prompt(cc)
        self.assertIn("includes test changes", prompt)


class TestCommitGeneratorOllama(unittest.TestCase):
    def _gen(self, model="gemma3:1b"):
        return CommitGenerator(CommitGeneratorConfig(model=model))

    @patch("commit_generator.OllamaClient")
    def test_uses_ollama_when_available(self, MockClient):
        instance = MockClient.return_value
        instance.generate.return_value = "feat(auth): add login endpoint"
        cc = _make_cc([ChangedFile("src/auth.py", "added", 10, 0)])
        draft = self._gen().generate(cc)
        self.assertEqual(draft.message, "feat(auth): add login endpoint")
        self.assertEqual(draft.source, "ollama:gemma3:1b")
        self.assertFalse(draft.fallback)

    @patch("commit_generator.OllamaClient")
    def test_falls_back_on_unavailable(self, MockClient):
        instance = MockClient.return_value
        instance.generate.side_effect = OllamaUnavailableError("connection refused")
        cc = _make_cc([ChangedFile("src/fix.py", "modified", 2, 1)])
        draft = self._gen().generate(cc)
        self.assertEqual(draft.source, "heuristic")
        self.assertIn("ollama unavailable", draft.rationale)

    @patch("commit_generator.OllamaClient")
    def test_falls_back_on_invalid_model_output(self, MockClient):
        instance = MockClient.return_value
        instance.generate.return_value = "This is not a conventional commit message at all."
        cc = _make_cc([ChangedFile("src/x.py", "modified", 1, 1)])
        draft = self._gen().generate(cc)
        self.assertEqual(draft.source, "heuristic")

    def test_no_model_uses_heuristic_directly(self):
        gen = CommitGenerator(CommitGeneratorConfig(model=""))
        cc = _make_cc([ChangedFile("src/y.py", "modified", 3, 0)])
        draft = gen.generate(cc)
        self.assertEqual(draft.source, "heuristic")
