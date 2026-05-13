"""Unit tests for LLMRouter policy and fallback behavior."""

import unittest
from unittest.mock import MagicMock

from llm.contracts import LLMResponse
from llm.router import LLMRouter, LLMRouterConfig


def _provider(name: str, response: LLMResponse, available: bool = True):
    provider = MagicMock()
    provider.name = name
    provider.is_available.return_value = available
    provider.embed.return_value = response
    provider.generate.return_value = response
    return provider


class TestLLMRouter(unittest.TestCase):
    def test_local_first_uses_local(self):
        local = _provider("ollama", LLMResponse(provider="ollama", model="m1", latency_ms=5, text="ok"))
        remote = _provider("openrouter", LLMResponse(provider="openrouter", model="m2", latency_ms=5, text="ok"))
        router = LLMRouter(local, remote, LLMRouterConfig(mode="local-first"))

        result = router.generate("prompt", local_model="m1", remote_model="m2")
        self.assertTrue(result.ok)
        self.assertEqual(result.provider, "ollama")

    def test_fallback_to_remote_when_local_unavailable(self):
        local = _provider("ollama", LLMResponse(provider="ollama", model="m1", latency_ms=5, text="ok"), available=False)
        remote = _provider("openrouter", LLMResponse(provider="openrouter", model="m2", latency_ms=5, text="ok"))
        router = LLMRouter(local, remote, LLMRouterConfig(mode="local-first"))

        result = router.generate("prompt", local_model="m1", remote_model="m2")
        self.assertTrue(result.ok)
        self.assertEqual(result.provider, "openrouter")

    def test_remote_only_fails_without_token(self):
        local = _provider("ollama", LLMResponse(provider="ollama", model="m1", latency_ms=5, text="ok"))
        remote = _provider(
            "openrouter",
            LLMResponse(provider="openrouter", model="m2", latency_ms=0, error_reason="provider unavailable: missing CC_OPENROUTER_API_KEY"),
            available=False,
        )
        router = LLMRouter(local, remote, LLMRouterConfig(mode="remote-only"))

        result = router.generate("prompt", local_model="m1", remote_model="m2")
        self.assertFalse(result.ok)
        self.assertIn("provider unavailable", result.error_reason)
