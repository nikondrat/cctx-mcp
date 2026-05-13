"""Tests that AGENTS.md commit flow section is properly enforced."""

import unittest
from pathlib import Path


AGENTS_MD = Path(__file__).parent.parent / "AGENTS.md"


class TestCommitFlowEnforcement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(AGENTS_MD, encoding="utf-8") as f:
            cls.content = f.read()

    def test_commit_flow_section_exists_with_mandatory_header(self):
        self.assertIn(
            "## Commit Flow — ABSOLUTE REQUIREMENT",
            self.content,
            "AGENTS.md must contain '## Commit Flow — ABSOLUTE REQUIREMENT' header",
        )

    def test_contains_compact_change_intelligence(self):
        self.assertIn("compact_change_intelligence", self.content)

    def test_contains_draft_commit(self):
        self.assertIn("draft_commit", self.content)

    def test_contains_approve_commit_draft(self):
        self.assertIn("approve_commit_draft", self.content)

    def test_forbids_direct_git_commit(self):
        markers = [
            "NEVER fall back to bash `git commit`",
            "You MUST NOT use:",
            "`git commit`",
        ]
        for marker in markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, self.content)

    def test_fallback_strategy_documented(self):
        self.assertIn(
            "approve_commit_draft(project_path, message='...')",
            self.content,
        )
        self.assertIn("NEVER fall back to bash `git commit`", self.content)
