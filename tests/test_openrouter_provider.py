"""Unit tests for OpenRouterProvider with mocked HTTP."""

import json
import unittest
from unittest.mock import MagicMock, patch

from llm.providers.openrouter import OpenRouterConfig, OpenRouterProvider


def _fake_response(body: dict):
    raw = json.dumps(body).encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = raw
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestOpenRouterProvider(unittest.TestCase):
    def _provider(self):
        return OpenRouterProvider(
            OpenRouterConfig(api_key="test-key", base_url="https://openrouter.ai/api/v1", timeout=5)
        )

    def test_unavailable_without_key(self):
        provider = OpenRouterProvider(OpenRouterConfig(api_key=""))
        self.assertFalse(provider.is_available())
        response = provider.generate("prompt", "openai/gpt-4o-mini")
        self.assertFalse(response.ok)
        self.assertIn("missing CC_OPENROUTER_API_KEY", response.error_reason)

    @patch("urllib.request.urlopen")
    def test_embed_success(self, mock_open):
        mock_open.return_value = _fake_response({"data": [{"embedding": [0.1, 0.2, 0.3]}]})
        response = self._provider().embed("query", "text-embedding-3-small")
        self.assertTrue(response.ok)
        self.assertEqual(response.embedding, [0.1, 0.2, 0.3])

    @patch("urllib.request.urlopen")
    def test_generate_success(self, mock_open):
        mock_open.return_value = _fake_response(
            {"choices": [{"message": {"content": "feat(api): add route"}}]}
        )
        response = self._provider().generate("prompt", "openai/gpt-4o-mini")
        self.assertTrue(response.ok)
        self.assertEqual(response.text, "feat(api): add route")
