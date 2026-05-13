"""Tests for server version and staleness detection."""

import json
import re
import unittest

from code_context.server import SERVER_VERSION, GIT_COMMIT, BUILD_TIMESTAMP


class TestServerVersion(unittest.TestCase):
    def test_version_is_semver(self):
        self.assertRegex(SERVER_VERSION, r"^\d+\.\d+\.\d+$")

    def test_git_commit_is_string(self):
        self.assertIsInstance(GIT_COMMIT, str)
        self.assertGreater(len(GIT_COMMIT), 0)

    def test_build_timestamp_is_iso_format(self):
        self.assertRegex(BUILD_TIMESTAMP, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_get_version_returns_valid_json(self):
        from code_context.server import get_version
        result = get_version()
        data = json.loads(result)
        self.assertIn("version", data)
        self.assertIn("commit", data)
        self.assertIn("built", data)
        self.assertEqual(data["version"], SERVER_VERSION)
        self.assertEqual(data["commit"], GIT_COMMIT)

    def test_get_version_json_is_parseable(self):
        from code_context.server import get_version
        data = json.loads(get_version())
        self.assertRegex(data["version"], r"^\d+\.\d+\.\d+$")
