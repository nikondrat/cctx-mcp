"""Contracts shared by all LLM providers and the router."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class LLMResponse:
    provider: str
    model: str
    latency_ms: int
    text: str = ""
    embedding: Optional[list[float]] = None
    error_reason: str = ""

    @property
    def ok(self) -> bool:
        return not self.error_reason


class LLMProvider(Protocol):
    name: str

    def is_available(self) -> bool:
        ...

    def embed(self, text: str, model: str) -> LLMResponse:
        ...

    def embed_batch(self, texts: list[str], model: str) -> list[LLMResponse]:
        ...

    def generate(self, prompt: str, model: str, options: Optional[dict] = None) -> LLMResponse:
        ...
