"""CLI entrypoint: uv run pre-index [project_path]

Pre-build vector index for a project and persist to disk.
"""

import os
import sys
import time
from pathlib import Path


def main():
    project_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    p = Path(project_path)
    if not p.exists():
        print(f"Error: project not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    from config import CodeContextConfig
    from llm.router import LLMRouter
    from llm.providers.ollama import OllamaProvider
    from llm.providers.openrouter import OpenRouterProvider
    from vector_index import VectorIndex

    cfg = CodeContextConfig()
    local = OllamaProvider(cfg.ollama_provider)
    remote = OpenRouterProvider(cfg.openrouter)
    router = LLMRouter(local_provider=local, remote_provider=remote, config=cfg.llm_router)

    idx = VectorIndex(
        str(p),
        router,
        local_model=cfg.embed_model,
        remote_model=cfg.openrouter_embed_model,
    )

    print(f"Indexing {project_path}...", file=sys.stderr)
    started = time.perf_counter()
    count = idx.index_project()
    elapsed = time.perf_counter() - started
    print(f"Done: {count} new chunks, {len(idx._chunks)} total in {elapsed:.1f}s", file=sys.stderr)
    print(f"Index saved to ~/.code-context-cache/vectors/", file=sys.stderr)


if __name__ == "__main__":
    main()
