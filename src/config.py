"""Feature flags and runtime configuration for incremental rollout."""

import os

from ollama_client import OllamaConfig


class CodeContextConfig:
    """Central configuration sourced from environment variables."""

    def __init__(self) -> None:
        self.semantic_summaries_enabled: bool = self._env_bool("CC_SEMANTIC_SUMMARIES", True)
        self.commit_drafting_enabled: bool = self._env_bool("CC_COMMIT_DRAFTING", True)

        # Ollama integration
        self.commit_model: str = os.environ.get("CC_COMMIT_MODEL", "gemma4:latest")
        self.embed_model: str = os.environ.get("CC_EMBED_MODEL", "nomic-embed-text")
        self.ollama: OllamaConfig = OllamaConfig(
            base_url=os.environ.get("CC_OLLAMA_URL", "http://localhost:11434"),
            timeout=int(os.environ.get("CC_OLLAMA_TIMEOUT", "10")),
        )

    def as_dict(self) -> dict:
        return {
            "semantic_summaries": self.semantic_summaries_enabled,
            "commit_drafting": self.commit_drafting_enabled,
            "commit_model": self.commit_model or "(heuristic fallback)",
            "embed_model": self.embed_model or "(disabled)",
            "ollama_url": self.ollama.base_url,
            "ollama_timeout": self.ollama.timeout,
        }

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        val = os.environ.get(name)
        if val is None:
            return default
        return val.lower() in ("1", "true", "yes", "on")
