"""Ollama provider adapter implementing the generic LLMProvider contract."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from code_context.llm.contracts import LLMResponse
from code_context.ollama_client import OllamaClient, OllamaConfig, OllamaUnavailableError


@dataclass
class OllamaProviderConfig:
    base_url: str = "http://localhost:11434"
    timeout: int = 10


class OllamaProvider:
    name = "ollama"

    def __init__(self, config: Optional[OllamaProviderConfig] = None) -> None:
        cfg = config or OllamaProviderConfig()
        self._client = OllamaClient(OllamaConfig(base_url=cfg.base_url, timeout=cfg.timeout))

    def is_available(self) -> bool:
        return self._client.is_available()

    def embed(self, text: str, model: str) -> LLMResponse:
        started = time.perf_counter()
        try:
            embedding = self._client.embed(model=model, text=text)
            latency = int((time.perf_counter() - started) * 1000)
            return LLMResponse(provider=self.name, model=model, latency_ms=latency, embedding=embedding)
        except OllamaUnavailableError as exc:
            latency = int((time.perf_counter() - started) * 1000)
            return LLMResponse(
                provider=self.name,
                model=model,
                latency_ms=latency,
                error_reason=f"provider unavailable: {exc}",
            )

    def generate(self, prompt: str, model: str, options: Optional[dict] = None) -> LLMResponse:
        opts = options or {}
        temperature = float(opts.get("temperature", 0.1))
        started = time.perf_counter()
        try:
            text = self._client.generate(model=model, prompt=prompt, temperature=temperature)
            latency = int((time.perf_counter() - started) * 1000)
            if not text.strip():
                return LLMResponse(
                    provider=self.name,
                    model=model,
                    latency_ms=latency,
                    error_reason="invalid response: empty text",
                )
            return LLMResponse(provider=self.name, model=model, latency_ms=latency, text=text)
        except OllamaUnavailableError as exc:
            latency = int((time.perf_counter() - started) * 1000)
            return LLMResponse(
                provider=self.name,
                model=model,
                latency_ms=latency,
                error_reason=f"provider unavailable: {exc}",
            )
