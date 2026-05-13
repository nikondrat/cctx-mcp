"""OpenRouter provider with Chat Completions and Embeddings support."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from code_context.llm.contracts import LLMResponse


@dataclass
class OpenRouterConfig:
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    timeout: int = 10
    max_tokens: int = 256
    temperature: float = 0.1


class OpenRouterProvider:
    name = "openrouter"

    def __init__(self, config: Optional[OpenRouterConfig] = None) -> None:
        self._cfg = config or OpenRouterConfig()

    def is_available(self) -> bool:
        return bool(self._cfg.api_key)

    def embed(self, text: str, model: str) -> LLMResponse:
        started = time.perf_counter()
        if not self._cfg.api_key:
            return LLMResponse(
                provider=self.name,
                model=model,
                latency_ms=0,
                error_reason="provider unavailable: missing CC_OPENROUTER_API_KEY",
            )

        payload = {
            "model": model,
            "input": text,
        }
        try:
            response = self._post("/embeddings", payload)
            data = response.get("data") or []
            embedding = (data[0] or {}).get("embedding") if data else None
            latency = int((time.perf_counter() - started) * 1000)
            if not embedding:
                return LLMResponse(
                    provider=self.name,
                    model=model,
                    latency_ms=latency,
                    error_reason="invalid response: missing embedding",
                )
            return LLMResponse(provider=self.name, model=model, latency_ms=latency, embedding=embedding)
        except TimeoutError:
            latency = int((time.perf_counter() - started) * 1000)
            return LLMResponse(provider=self.name, model=model, latency_ms=latency, error_reason="timeout")
        except Exception as exc:
            latency = int((time.perf_counter() - started) * 1000)
            return LLMResponse(
                provider=self.name,
                model=model,
                latency_ms=latency,
                error_reason=f"provider unavailable: {exc}",
            )

    def generate(self, prompt: str, model: str, options: Optional[dict] = None) -> LLMResponse:
        started = time.perf_counter()
        if not self._cfg.api_key:
            return LLMResponse(
                provider=self.name,
                model=model,
                latency_ms=0,
                error_reason="provider unavailable: missing CC_OPENROUTER_API_KEY",
            )

        opts = options or {}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(opts.get("temperature", self._cfg.temperature)),
            "max_tokens": int(opts.get("max_tokens", self._cfg.max_tokens)),
        }
        try:
            response = self._post("/chat/completions", payload)
            choices = response.get("choices") or []
            message = ((choices[0] or {}).get("message") or {}).get("content", "") if choices else ""
            text = (message or "").strip()
            latency = int((time.perf_counter() - started) * 1000)
            if not text:
                return LLMResponse(
                    provider=self.name,
                    model=model,
                    latency_ms=latency,
                    error_reason="invalid response: empty text",
                )
            return LLMResponse(provider=self.name, model=model, latency_ms=latency, text=text)
        except TimeoutError:
            latency = int((time.perf_counter() - started) * 1000)
            return LLMResponse(provider=self.name, model=model, latency_ms=latency, error_reason="timeout")
        except Exception as exc:
            latency = int((time.perf_counter() - started) * 1000)
            return LLMResponse(
                provider=self.name,
                model=model,
                latency_ms=latency,
                error_reason=f"provider unavailable: {exc}",
            )

    def _post(self, path: str, payload: dict) -> dict:
        if not self._cfg.api_key:
            raise RuntimeError("missing api key")

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._cfg.base_url}{path}",
            data=data,
            headers={
                "Authorization": f"Bearer {self._cfg.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/code-context/code-context",
                "X-Title": "code-context",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._cfg.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            if exc.code == 408:
                raise TimeoutError("request timeout") from exc
            raise RuntimeError(f"HTTP {exc.code}: {body[:160]}") from exc
        except (urllib.error.URLError, OSError) as exc:
            if isinstance(exc.reason, TimeoutError):
                raise TimeoutError("request timeout") from exc
            raise RuntimeError(str(exc)) from exc
