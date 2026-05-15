"""MCP Server for code-context — efficient code analysis for AI agents."""

import json
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from code_context.context import instrument_tool

SERVER_VERSION = "0.6.0"

try:
    _commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, timeout=5,
    )
    GIT_COMMIT = _commit.stdout.strip() or "unknown"
    _ts = subprocess.run(
        ["git", "log", "-1", "--format=%cI"],
        capture_output=True, text=True, timeout=5,
    )
    BUILD_TIMESTAMP = _ts.stdout.strip() or datetime.now().isoformat()
except Exception:
    GIT_COMMIT = "unknown"
    BUILD_TIMESTAMP = datetime.now().isoformat()

mcp = FastMCP("code-context")

from code_context import handlers

_TOOL_REGISTRATIONS = [
    ("smart_read", handlers.tool_smart_read),
    ("find_symbols", handlers.tool_find_symbols),
    ("get_dependencies", handlers.tool_get_dependencies),
    ("trace_calls", handlers.tool_trace_calls),
    ("analyze_project", handlers.tool_analyze_project),
    ("get_symbol_summaries", handlers.tool_get_symbol_summaries),
    ("get_config", handlers.tool_get_config),
    ("compact_change_intelligence", handlers.tool_compact_change_intelligence),
    ("draft_commit", handlers.tool_draft_commit),
    ("approve_commit_draft", handlers.tool_approve_commit_draft),
    ("list_tools", handlers.tool_list_tools),
]

for name, fn in _TOOL_REGISTRATIONS:
    mcp.tool(name=name)(instrument_tool(name)(fn))


@mcp.tool()
@instrument_tool("get_version")
def get_version() -> str:
    """Show server version, git commit, and build timestamp for staleness detection."""
    return json.dumps({"version": SERVER_VERSION, "commit": GIT_COMMIT, "built": BUILD_TIMESTAMP})


@mcp.tool()
@instrument_tool("get_health")
def get_health() -> str:
    """Show aggregated health status of all system dependencies."""
    base = handlers.tool_get_health()
    data = json.loads(base)
    data["server"] = {"version": SERVER_VERSION, "commit": GIT_COMMIT}
    return json.dumps(data)


def main():
    """Run the MCP server with optional pre-indexing."""
    import argparse
    import os

    from code_context.config import CodeContextConfig
    from code_context.llm.providers.ollama import OllamaProvider
    from code_context.llm.providers.openrouter import OpenRouterProvider
    from code_context.llm.router import LLMRouter
    from code_context.vector_index import VectorIndex

    src_path = Path(__file__).parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    parser = argparse.ArgumentParser(description="code-context MCP server")
    parser.add_argument("--skip-index", action="store_true", help="Skip vector index pre-build on startup")
    parser.add_argument("--project", type=str, default=None, help="Project path for pre-indexing")
    args, _ = parser.parse_known_args()

    if not args.skip_index:
        project_path = args.project or os.environ.get("CC_PROJECT_PATH") or os.getcwd()
        p = Path(project_path)
        if p.exists():
            print(f"Pre-building vector index for {project_path}...", file=sys.stderr)
            try:
                cfg = CodeContextConfig()
                local = OllamaProvider(cfg.ollama_provider)
                remote = OpenRouterProvider(cfg.openrouter)
                router = LLMRouter(local_provider=local, remote_provider=remote, config=cfg.llm_router)
                idx = VectorIndex(project_path, router, local_model=cfg.embed_model, remote_model=cfg.openrouter_embed_model)
                done = threading.Event()

                def _build():
                    try:
                        idx.index_project()
                        handlers._vector_indexes[project_path] = idx
                    except Exception as e:
                        print(f"Index build error (will use lazy): {e}", file=sys.stderr)
                    finally:
                        done.set()

                t = threading.Thread(target=_build, daemon=True)
                t.start()
                if not done.wait(timeout=30):
                    print("Index build timed out (30s), continuing with lazy index", file=sys.stderr)
                else:
                    print(f"Index built: {len(idx._chunks)} chunks from {project_path}", file=sys.stderr)
            except Exception as e:
                print(f"Index pre-build skipped: {e}", file=sys.stderr)

    mcp.run()


if __name__ == "__main__":
    main()
