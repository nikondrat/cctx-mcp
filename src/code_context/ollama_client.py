"""HTTP transport layer for Ollama API — embedding and text generation only."""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    timeout: int = 10


class OllamaUnavailableError(Exception):
    """Raised when Ollama is unreachable or returns a non-200 response."""


class OllamaClient:
    """Low-level HTTP client for Ollama /api/* endpoints.

    Responsibilities: serialize requests, deserialize responses, surface
    connection/timeout errors as OllamaUnavailableError.  No business logic.
    """

    def __init__(self, config: Optional[OllamaConfig] = None) -> None:
        self._cfg = config or OllamaConfig()

    # ── public API ────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Return True if Ollama is reachable (HEAD /)."""
        try:
            req = urllib.request.Request(
                f"{self._cfg.base_url}/",
                method="HEAD",
            )
            with urllib.request.urlopen(req, timeout=self._cfg.timeout):
                return True
        except Exception:
            return False

    def embed(self, model: str, text: str) -> list[float]:
        """Return embedding vector for *text* using *model*.

        Raises OllamaUnavailableError on any network or HTTP error.
        """
        payload = {"model": model, "prompt": text}
        response = self._post("/api/embeddings", payload)
        embedding = response.get("embedding")
        if not embedding:
            raise OllamaUnavailableError(f"No embedding in response: {response}")
        return embedding

    def generate(self, model: str, prompt: str, temperature: float = 0.1) -> str:
        """Return generated text (non-streaming) for *prompt* using *model*.

        Raises OllamaUnavailableError on any network or HTTP error.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        response = self._post("/api/generate", payload)
        text = response.get("response", "").strip()
        if not text:
            raise OllamaUnavailableError(f"Empty response from model: {response}")
        return text

    def list_models(self) -> list[str]:
        """Return names of locally available models."""
        try:
            response = self._get("/api/tags")
            return [m["name"] for m in response.get("models", [])]
        except OllamaUnavailableError:
            return []

    # ── internals ─────────────────────────────────────────────────────────

    def _post(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{self._cfg.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._send(req)

    def _get(self, path: str) -> dict:
        req = urllib.request.Request(
            f"{self._cfg.base_url}{path}",
            method="GET",
        )
        return self._send(req)

    def _send(self, req: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(req, timeout=self._cfg.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raise OllamaUnavailableError(f"HTTP {exc.code}: {exc.reason}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OllamaUnavailableError(str(exc)) from exc
