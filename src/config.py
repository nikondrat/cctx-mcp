"""Feature flags and runtime configuration for incremental rollout."""

import os

from llm.providers.ollama import OllamaProviderConfig
from llm.providers.openrouter import OpenRouterConfig
from llm.router import LLMRouterConfig
from ollama_client import OllamaConfig


class CodeContextConfig:
    """Central configuration sourced from environment variables."""

    def __init__(self) -> None:
        self.semantic_summaries_enabled: bool = self._env_bool("CC_SEMANTIC_SUMMARIES", True)
        self.commit_drafting_enabled: bool = self._env_bool("CC_COMMIT_DRAFTING", True)

        # Router strategy
        self.llm_router: LLMRouterConfig = LLMRouterConfig(
            mode=os.environ.get("CC_LLM_ROUTER", "local-first"),
            local_provider_name=os.environ.get("CC_LOCAL_PROVIDER", "ollama"),
            remote_provider_name=os.environ.get("CC_REMOTE_PROVIDER", "openrouter"),
        )

        # Ollama integration
        self.commit_model: str = os.environ.get("CC_COMMIT_MODEL", "gemma4:latest")
        self.embed_model: str = os.environ.get("CC_EMBED_MODEL", "nomic-embed-text")
        self.ollama_provider: OllamaProviderConfig = OllamaProviderConfig(
            base_url=os.environ.get("CC_OLLAMA_URL", "http://localhost:11434"),
            timeout=int(os.environ.get("CC_OLLAMA_TIMEOUT", "10")),
        )

        # Backward compatibility for existing code/tests
        self.ollama: OllamaConfig = OllamaConfig(
            base_url=self.ollama_provider.base_url,
            timeout=self.ollama_provider.timeout,
        )

        # OpenRouter integration
        self.openrouter_embed_model: str = os.environ.get("CC_OPENROUTER_EMBED_MODEL", "text-embedding-3-small")
        self.openrouter_commit_model: str = os.environ.get("CC_OPENROUTER_COMMIT_MODEL", "openai/gpt-4o-mini")
        self.openrouter: OpenRouterConfig = OpenRouterConfig(
            api_key=os.environ.get("CC_OPENROUTER_API_KEY", ""),
            base_url=os.environ.get("CC_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            timeout=int(os.environ.get("CC_OPENROUTER_TIMEOUT", os.environ.get("CC_OLLAMA_TIMEOUT", "10"))),
            max_tokens=int(os.environ.get("CC_OPENROUTER_MAX_TOKENS", "256")),
            temperature=float(os.environ.get("CC_OPENROUTER_TEMPERATURE", "0.1")),
        )

    def as_dict(self) -> dict:
        return {
            "semantic_summaries": self.semantic_summaries_enabled,
            "commit_drafting": self.commit_drafting_enabled,
            "commit_model": self.commit_model or "(heuristic fallback)",
            "embed_model": self.embed_model or "(disabled)",
            "llm_router": self.llm_router.mode,
            "local_provider": self.llm_router.local_provider_name,
            "remote_provider": self.llm_router.remote_provider_name,
            "ollama_url": self.ollama.base_url,
            "ollama_timeout": self.ollama.timeout,
            "openrouter_base_url": self.openrouter.base_url,
            "openrouter_timeout": self.openrouter.timeout,
            "openrouter_embed_model": self.openrouter_embed_model,
            "openrouter_commit_model": self.openrouter_commit_model,
            "openrouter_max_tokens": self.openrouter.max_tokens,
            "openrouter_temperature": self.openrouter.temperature,
            "openrouter_api_key": "set" if self.openrouter.api_key else "(missing)",
        }

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        val = os.environ.get(name)
        if val is None:
            return default
        return val.lower() in ("1", "true", "yes", "on")
