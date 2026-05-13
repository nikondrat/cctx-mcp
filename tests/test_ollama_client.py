"""Unit tests for OllamaClient — all network calls are mocked."""

import json
import unittest
from io import BytesIO
from unittest.mock import MagicMock, patch

from code_context.ollama_client import OllamaClient, OllamaConfig, OllamaUnavailableError


def _fake_response(body: dict, status: int = 200):
    raw = json.dumps(body).encode()
    resp = MagicMock()
    resp.read.return_value = raw
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestOllamaClientEmbed(unittest.TestCase):
    def _client(self):
        return OllamaClient(OllamaConfig(base_url="http://localhost:11434", timeout=5))

    @patch("urllib.request.urlopen")
    def test_embed_returns_vector(self, mock_open):
        mock_open.return_value = _fake_response({"embedding": [0.1, 0.2, 0.3]})
        result = self._client().embed("nomic-embed-text", "hello world")
        self.assertEqual(result, [0.1, 0.2, 0.3])

    @patch("urllib.request.urlopen")
    def test_embed_raises_on_empty(self, mock_open):
        mock_open.return_value = _fake_response({"embedding": []})
        with self.assertRaises(OllamaUnavailableError):
            self._client().embed("nomic-embed-text", "text")

    @patch("urllib.request.urlopen", side_effect=OSError("connection refused"))
    def test_embed_raises_on_connection_error(self, _):
        with self.assertRaises(OllamaUnavailableError):
            self._client().embed("nomic-embed-text", "text")


class TestOllamaClientEmbedBatch(unittest.TestCase):
    def _client(self):
        return OllamaClient(OllamaConfig(base_url="http://localhost:11434", timeout=5))

    @patch("urllib.request.urlopen")
    def test_embed_batch_returns_vectors(self, mock_open):
        mock_open.return_value = _fake_response(
            {"model": "nomic-embed-text", "embeddings": [[0.1, 0.2], [0.3, 0.4]]}
        )
        result = self._client().embed_batch("nomic-embed-text", ["a", "b"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], [0.1, 0.2])
        self.assertEqual(result[1], [0.3, 0.4])

    @patch("urllib.request.urlopen", side_effect=OllamaUnavailableError("HTTP 404"))
    def test_embed_batch_fallback_on_404(self, mock_open):
        with patch.object(OllamaClient, "embed", return_value=[0.5, 0.6]) as mock_embed:
            result = self._client().embed_batch("nomic-embed-text", ["a", "b"])
            self.assertEqual(mock_embed.call_count, 2)
            self.assertEqual(len(result), 2)

    @patch("urllib.request.urlopen")
    def test_embed_batch_raises_on_mismatch(self, mock_open):
        mock_open.return_value = _fake_response(
            {"model": "nomic-embed-text", "embeddings": [[0.1, 0.2]]}
        )
        with self.assertRaises(OllamaUnavailableError):
            self._client().embed_batch("nomic-embed-text", ["a", "b"])


class TestOllamaClientGenerate(unittest.TestCase):
    def _client(self):
        return OllamaClient(OllamaConfig())

    @patch("urllib.request.urlopen")
    def test_generate_returns_stripped_text(self, mock_open):
        mock_open.return_value = _fake_response({"response": "  feat: add login  \n"})
        result = self._client().generate("gemma3:1b", "prompt")
        self.assertEqual(result, "feat: add login")

    @patch("urllib.request.urlopen")
    def test_generate_raises_on_empty_response(self, mock_open):
        mock_open.return_value = _fake_response({"response": "   "})
        with self.assertRaises(OllamaUnavailableError):
            self._client().generate("gemma3:1b", "prompt")

    @patch("urllib.request.urlopen", side_effect=TimeoutError())
    def test_generate_raises_on_timeout(self, _):
        with self.assertRaises(OllamaUnavailableError):
            self._client().generate("gemma3:1b", "prompt")


class TestOllamaClientAvailability(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_is_available_true(self, mock_open):
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        self.assertTrue(OllamaClient().is_available())

    @patch("urllib.request.urlopen", side_effect=OSError())
    def test_is_available_false(self, _):
        self.assertFalse(OllamaClient().is_available())
