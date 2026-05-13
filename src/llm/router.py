"""Routing policy between local and remote LLM providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from llm.contracts import LLMProvider, LLMResponse

RoutingMode = str


@dataclass
class LLMRouterConfig:
    mode: RoutingMode = "local-first"
    local_provider_name: str = "ollama"
    remote_provider_name: str = "openrouter"


class LLMRouter:
    def __init__(
        self,
        local_provider: Optional[LLMProvider],
        remote_provider: Optional[LLMProvider],
        config: Optional[LLMRouterConfig] = None,
    ) -> None:
        self._cfg = config or LLMRouterConfig()
        self._providers = {
            self._cfg.local_provider_name: local_provider,
            self._cfg.remote_provider_name: remote_provider,
        }

    def embed(
        self,
        text: str,
        local_model: str,
        remote_model: str,
        force_provider: Optional[str] = None,
    ) -> LLMResponse:
        return self._run(
            op="embed",
            payload=text,
            local_model=local_model,
            remote_model=remote_model,
            options=None,
            force_provider=force_provider,
        )

    def generate(
        self,
        prompt: str,
        local_model: str,
        remote_model: str,
        options: Optional[dict] = None,
        force_provider: Optional[str] = None,
    ) -> LLMResponse:
        return self._run(
            op="generate",
            payload=prompt,
            local_model=local_model,
            remote_model=remote_model,
            options=options or {},
            force_provider=force_provider,
        )

    def _run(
        self,
        op: str,
        payload: str,
        local_model: str,
        remote_model: str,
        options: Optional[dict],
        force_provider: Optional[str],
    ) -> LLMResponse:
        providers = [force_provider] if force_provider else self._provider_order()
        errors: list[str] = []

        for name in providers:
            provider = self._providers.get(name)
            if provider is None:
                errors.append(f"provider unavailable: {name} not configured")
                continue
            if not provider.is_available():
                errors.append(f"provider unavailable: {name}")
                continue

            model = local_model if name == self._cfg.local_provider_name else remote_model
            if not model:
                errors.append(f"provider unavailable: missing model for {name}")
                continue

            if op == "embed":
                result = provider.embed(payload, model=model)
            else:
                result = provider.generate(payload, model=model, options=options)

            if result.ok:
                return result
            errors.append(result.error_reason or f"provider unavailable: {name}")

        return LLMResponse(
            provider=providers[-1] if providers else "none",
            model=remote_model or local_model,
            latency_ms=0,
            error_reason="; ".join(errors) if errors else "provider unavailable",
        )

    def _provider_order(self) -> list[str]:
        local = self._cfg.local_provider_name
        remote = self._cfg.remote_provider_name
        if self._cfg.mode == "local-only":
            return [local]
        if self._cfg.mode == "remote-first":
            return [remote, local]
        if self._cfg.mode == "remote-only":
            return [remote]
        return [local, remote]
