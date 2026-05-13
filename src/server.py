"""MCP Server for code-context - efficient code analysis for AI agents."""

import asyncio
import functools
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP


SERVER_VERSION = "0.2.0"

try:
    _commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, timeout=5,
    )
    GIT_COMMIT = _commit.stdout.strip() or "unknown"
except Exception:
    GIT_COMMIT = "unknown"

BUILD_TIMESTAMP = datetime.now().isoformat()

from cache import Cache, _file_hash
from change_intel import CompactChangeIntel, CommitGate
from commit_generator import CommitGenerator, CommitGeneratorConfig
from config import CodeContextConfig
from llm.providers.ollama import OllamaProvider
from llm.providers.openrouter import OpenRouterProvider
from llm.router import LLMRouter
from metrics import get_metrics
from search import ProjectSearch
from summaries import SemanticSummarizer
from vector_index import VectorIndex

# Commit gate singleton
_commit_gate: Optional[CommitGate] = None


def get_commit_gate() -> CommitGate:
    global _commit_gate
    if _commit_gate is None:
        _commit_gate = CommitGate()
    return _commit_gate


# Create MCP server
mcp = FastMCP("code-context")

# Global cache, search, and vector index instances
_cache: Optional[Cache] = None
_searches: dict[str, ProjectSearch] = {}
_vector_indexes: dict[str, VectorIndex] = {}
_llm_router: Optional[LLMRouter] = None


def _result_ok(result: Any) -> bool:
    if isinstance(result, str):
        lowered = result.lower()
        if lowered.startswith("error:"):
            return False
        if " unavailable" in lowered:
            return False
        if " failed" in lowered:
            return False
    return True


def _instrument_tool(tool_name: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            started = time.perf_counter()
            ok = True
            try:
                result = func(*args, **kwargs)
                ok = _result_ok(result)
                return result
            except Exception:
                ok = False
                raise
            finally:
                latency_ms = int((time.perf_counter() - started) * 1000)
                get_metrics().record_call(tool_name, latency_ms=latency_ms, ok=ok)

        return wrapper

    return decorator


def _get_config() -> CodeContextConfig:
    return CodeContextConfig()


def _get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        cfg = _get_config()
        local = OllamaProvider(cfg.ollama_provider)
        remote = OpenRouterProvider(cfg.openrouter)
        _llm_router = LLMRouter(local_provider=local, remote_provider=remote, config=cfg.llm_router)
    return _llm_router


def _get_vector_index(project_path: str) -> Optional[VectorIndex]:
    cfg = _get_config()
    if not cfg.embed_model and not cfg.openrouter_embed_model:
        return None
    if project_path not in _vector_indexes:
        _vector_indexes[project_path] = VectorIndex(
            project_path,
            _get_llm_router(),
            local_model=cfg.embed_model,
            remote_model=cfg.openrouter_embed_model,
        )
    return _vector_indexes[project_path]


def get_cache() -> Cache:
    """Get or create cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache


def get_search(project_path: str) -> ProjectSearch:
    """Get or create search instance for a project."""
    if project_path not in _searches:
        _searches[project_path] = ProjectSearch(Path(project_path), get_cache())
    return _searches[project_path]


@mcp.tool()
@_instrument_tool("smart_read")
def smart_read(file_path: str, project_path: Optional[str] = None) -> str:
    """Read a file and return structured analysis instead of full content.

    Returns:
        - File summary
        - Symbol structure (classes, functions, methods)
        - Dependencies
        - Line counts per symbol
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    if project_path:
        search = get_search(project_path)
    else:
        # Try to find project root
        search = ProjectSearch(path.parent, get_cache())

    result = search.smart_read(path)
    if result is None:
        return f"Error: Could not analyze file: {file_path}"

    return result


@mcp.tool()
@_instrument_tool("find_symbols")
def find_symbols(
    project_path: str,
    name: Optional[str] = None,
    symbol_type: Optional[str] = None,
) -> str:
    """Find symbols across a project by name or type.

    Args:
        project_path: Path to the project root
        name: Optional symbol name to search for (case-insensitive)
        symbol_type: Optional symbol type (function, class, method, interface, struct, enum, protocol, etc.)

    Returns:
        List of matching symbols with file, line, and doc comment
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    search = get_search(project_path)
    results = search.find_symbols(path, name=name, symbol_type=symbol_type)

    if not results:
        return "No symbols found matching criteria."

    output = [f"Found {len(results)} symbols:"]
    for r in results:
        line = f"  {r['file']}:{r['line']} - {r['type']} {r['name']}"
        if r.get("doc_comment"):
            line += f" // {r['doc_comment']}"
        output.append(line)

    return "\n".join(output)


@mcp.tool()
@_instrument_tool("get_dependencies")
def get_dependencies(file_path: str, project_path: Optional[str] = None) -> str:
    """Get dependencies/imports of a file.

    Returns:
        List of modules/files this file depends on
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    if project_path:
        search = get_search(project_path)
    else:
        search = ProjectSearch(path.parent, get_cache())

    deps = search.get_dependencies(path)
    if deps is None:
        return f"Error: Could not analyze file: {file_path}"

    if not deps:
        return "No dependencies found."

    return f"Dependencies for {file_path}:\n" + "\n".join(f"  - {dep}" for dep in deps)


@mcp.tool()
@_instrument_tool("trace_calls")
def trace_calls(symbol_name: str, project_path: str) -> str:
    """Find where a symbol is called/used across the project.

    Args:
        symbol_name: Name of the symbol to trace
        project_path: Path to the project root

    Returns:
        List of files and lines where the symbol is used
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    search = get_search(project_path)
    results = search.trace_calls(symbol_name, path)

    if not results:
        return f"No usages found for symbol: {symbol_name}"

    output = [f"Found {len(results)} usages of '{symbol_name}':"]
    for r in results:
        output.append(f"  {r['file']}:{r['line']} - {r['context']}")

    return "\n".join(output)


@mcp.tool()
@_instrument_tool("analyze_project")
def analyze_project(project_path: str, max_depth: int = 2) -> str:
    """Analyze overall project structure.

    Args:
        project_path: Path to the project root
        max_depth: Maximum directory depth to scan (default: 2)

    Returns:
        Project structure with file counts and languages
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    from search import LANGUAGE_EXTENSIONS

    stats = {"files": 0, "languages": {}, "directories": 0}

    for root, dirs, files in os.walk(path):
        # Limit depth
        rel_path = Path(root).relative_to(path)
        if len(rel_path.parts) > max_depth:
            dirs.clear()
            continue

        stats["directories"] += 1

        # Filter directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "Pods", "build", "dist", ".git", "__pycache__", "venv", ".venv")]

        for file in files:
            file_path = Path(root) / file
            ext = file_path.suffix.lower()
            if ext in LANGUAGE_EXTENSIONS:
                stats["files"] += 1
                lang = LANGUAGE_EXTENSIONS[ext].__name__.replace("Analyzer", "").lower()
                stats["languages"][lang] = stats["languages"].get(lang, 0) + 1

    output = [f"Project: {project_path}"]
    output.append(f"Total source files: {stats['files']}")
    output.append(f"Directories scanned: {stats['directories']}")
    output.append("")
    output.append("Languages:")
    for lang, count in sorted(stats["languages"].items(), key=lambda x: x[1], reverse=True):
        output.append(f"  {lang}: {count} files")

    return "\n".join(output)


@mcp.tool()
@_instrument_tool("get_symbol_summaries")
def get_symbol_summaries(file_path: str, project_path: Optional[str] = None) -> str:
    """Get semantic summaries for all symbols in a file.

    Returns summary metadata (purpose, behavior, dependencies, source, confidence)
    per symbol, generated lazily and cached.

    Args:
        file_path: Path to the file to summarize
        project_path: Optional project root for context

    Returns:
        Structured summary metadata for each symbol
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"

    if project_path:
        search = get_search(project_path)
    else:
        search = ProjectSearch(path.parent, get_cache())

    analysis = search._analyze_file(path)
    if not analysis:
        return f"Error: Could not analyze file: {file_path}"

    fh = _file_hash(path)
    summarizer = SemanticSummarizer(get_cache())
    summaries = summarizer.summarize_file(analysis, fh)
    if not summaries:
        return "No summaries generated."

    output = [f"Semantic summaries for {file_path}:"]
    for ss in summaries:
        sd = ss.to_dict()
        output.append(f"\n  {sd['purpose'][:80]}")
        output.append(f"    behavior: {sd['behavior'][:120]}")
        output.append(f"    confidence: {sd['confidence']} ({sd['source']})")
        output.append(f"    last_updated: {sd['last_updated']}")
    return "\n".join(output)


@mcp.tool()
@_instrument_tool("code_search")
def code_search(
    project_path: str,
    pattern: str,
    use_regex: bool = False,
    file_pattern: Optional[str] = None,
    case_sensitive: bool = False,
    context_lines: int = 2,
    max_results: int = 50,
) -> str:
    """Search file contents across a project (grep replacement).

    Args:
        project_path: Path to the project root
        pattern: Text or regex pattern to search for
        use_regex: Treat pattern as a regular expression
        file_pattern: Glob pattern to filter files (e.g. "*.swift", "**/*Interactor*")
        case_sensitive: Case-sensitive search
        context_lines: Number of context lines before/after each match
        max_results: Maximum number of matches to return

    Returns:
        Matches with file, line, text, and surrounding context
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    search = get_search(project_path)
    results = search.code_search(
        pattern,
        use_regex=use_regex,
        file_pattern=file_pattern,
        case_sensitive=case_sensitive,
        context_lines=context_lines,
        max_results=max_results,
    )

    if not results:
        return "No matches found."

    if "error" in results[0]:
        return f"Error: {results[0]['error']}"

    output = [f"Found {len(results)} matches for '{pattern}':"]
    for r in results:
        output.append("")
        output.append(f"  {r['file']}:{r['line']}")
        output.append(r["context"])

    return "\n".join(output)


@mcp.tool()
@_instrument_tool("find_files")
def find_files(
    project_path: str,
    name_pattern: Optional[str] = None,
    extension: Optional[str] = None,
    path_contains: Optional[str] = None,
    max_depth: Optional[int] = None,
    max_results: int = 50,
) -> str:
    """Find files by name, extension, or path (find/ls replacement).

    Args:
        project_path: Path to the project root
        name_pattern: Glob pattern for filename (e.g. "*Interactor*", "*.swift")
        extension: File extension without dot (e.g. "swift", "py")
        path_contains: Substring that must appear in the relative path
        max_depth: Maximum directory depth to search
        max_results: Maximum number of results

    Returns:
        List of files with short relative paths, sizes, and line counts
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    search = get_search(project_path)
    results = search.find_files(
        name_pattern=name_pattern,
        extension=extension,
        path_contains=path_contains,
        max_depth=max_depth,
        max_results=max_results,
    )

    if not results:
        return "No files found matching criteria."

    output = [f"Found {len(results)} files:"]
    for r in results:
        output.append(f"  {r['path']}  ({r['size_kb']} KB, {r['lines']} lines, {r['modified']})")

    return "\n".join(output)


@mcp.tool()
@_instrument_tool("dir_summary")
def dir_summary(
    project_path: str,
    dir_path: Optional[str] = None,
    depth: int = 1,
) -> str:
    """Summarize a directory's structure (ls -la replacement).

    Args:
        project_path: Path to the project root
        dir_path: Relative path within project (or None for root)
        depth: How many levels deep to show subdirectories

    Returns:
        Structured summary with subdirectories, file counts by type, and sizes
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    search = get_search(project_path)
    return search.dir_summary(dir_path=dir_path, depth=depth)


@mcp.tool()
@_instrument_tool("semantic_search")
def semantic_search(
    query: str,
    project_path: str,
    top_k: int = 5,
) -> str:
    """Search codebase by natural language query using routed embeddings.

    Fastest path for "find where X is done" questions — returns relevant code
    chunks ranked by semantic similarity, not full files.

    Args:
        query: Natural language description of what you're looking for
        project_path: Path to the project root
        top_k: Number of results to return (default 5)

    Returns:
        Ranked list of matching code chunks with file, line, symbol, and snippet
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    index = _get_vector_index(project_path)
    if index is None:
        return "semantic_search unavailable: no embedding model configured. Use find_symbols or code_search instead."

    try:
        results = index.search(query, top_k=top_k)
    except Exception as exc:
        return f"semantic_search error: {exc}"

    if not results:
        return "No results found. Try re-indexing or using find_symbols."

    lines = [f"Top {len(results)} results for: {query!r}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.file}:{r.line}  [{r.symbol}]  score={r.score}")
        lines.append(f"   {r.snippet[:120].replace(chr(10), ' ')}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
@_instrument_tool("get_config")
def get_config() -> str:
    """Show current feature flag configuration."""
    cfg = _get_config()
    lines = ["Current configuration:"]
    for k, v in cfg.as_dict().items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("Env vars: CC_SEMANTIC_SUMMARIES, CC_COMMIT_DRAFTING, CC_LLM_ROUTER,")
    lines.append("          CC_LOCAL_PROVIDER, CC_REMOTE_PROVIDER, CC_COMMIT_MODEL, CC_EMBED_MODEL,")
    lines.append("          CC_OLLAMA_URL, CC_OLLAMA_TIMEOUT, CC_OPENROUTER_API_KEY,")
    lines.append("          CC_OPENROUTER_BASE_URL, CC_OPENROUTER_TIMEOUT,")
    lines.append("          CC_OPENROUTER_EMBED_MODEL, CC_OPENROUTER_COMMIT_MODEL,")
    lines.append("          CC_OPENROUTER_MAX_TOKENS, CC_OPENROUTER_TEMPERATURE")
    return "\n".join(lines)


@mcp.tool()
@_instrument_tool("get_version")
def get_version() -> str:
    """Show server version, git commit, and build timestamp for staleness detection."""
    return json.dumps({
        "version": SERVER_VERSION,
        "commit": GIT_COMMIT,
        "built": BUILD_TIMESTAMP,
    })


@mcp.tool()
@_instrument_tool("get_metrics_report")
def get_metrics_report() -> str:
    """Show operational metrics (cache hit rate, latencies, etc.)."""
    return get_metrics().report()


@mcp.tool()
@_instrument_tool("get_metrics_events")
def get_metrics_events(limit: int = 25) -> str:
    """Show recent recorded tool-call events."""
    metrics = get_metrics()
    events = metrics.recent_events(limit=limit)
    if not events:
        return "No metrics events recorded yet."

    lines = [f"Recent metrics events ({len(events)}):"]
    for event in events:
        status = "ok" if event.get("ok") else "error"
        lines.append(
            f"  ts={event.get('ts')} tool={event.get('tool')} latency_ms={event.get('latency_ms')} status={status}"
        )
    return "\n".join(lines)


@mcp.tool()
@_instrument_tool("get_metrics_slowest")
def get_metrics_slowest(limit: int = 5) -> str:
    """Show the N slowest MCP tools by average latency.

    Args:
        limit: Number of tools to return (default 5)

    Returns:
        Formatted list of slowest tools with call count, latency, and errors
    """
    metrics = get_metrics()
    tools = metrics.slowest(limit=limit)
    if not tools:
        return "No tool metrics recorded yet."

    lines = [f"Top {len(tools)} slowest tools:"]
    for t in tools:
        lines.append(
            f"  {t['tool']}: {t['calls']} calls, "
            f"avg {t['avg_latency_ms']}ms, "
            f"total {t['total_latency_ms']}ms, "
            f"errors {t['errors']}"
        )
    return "\n".join(lines)


@mcp.tool()
@_instrument_tool("get_metrics_errors")
def get_metrics_errors() -> str:
    """Show tools with recorded errors and overall error rate.

    Returns:
        Formatted error summary per tool and total error rate
    """
    metrics = get_metrics()
    summary = metrics.errors_summary()
    if not summary["tools_with_errors"]:
        return "No errors recorded across any tool."

    lines = [f"Error summary ({summary['total_errors']}/{summary['total_calls']} calls, {summary['error_rate']:.2%}):"]
    for t in summary["tools_with_errors"]:
        lines.append(f"  {t['tool']}: {t['errors']} errors / {t['calls']} calls")
    return "\n".join(lines)


@mcp.tool()
@_instrument_tool("get_metrics_daily_trend")
def get_metrics_daily_trend(days: int = 7) -> str:
    """Show daily snapshot trend for the last N days, with token savings estimates.

    Triggers today's snapshot on first call of the day.

    Args:
        days: Number of days to show (default 7)

    Returns:
        Formatted daily trend with per-tool stats and estimated token savings
    """
    metrics = get_metrics()

    today = date.today().isoformat()
    today_file = metrics._daily_dir / f"{today}.json"
    if not today_file.exists():
        metrics._daily_snapshot()

    trend = metrics.get_daily_trend(days=days)
    lines = [f"Daily trend (last {len(trend)} days):\n"]
    for entry in trend:
        d = entry["date"]
        tools = entry.get("tools", {})
        savings = entry.get("total_savings_estimate_tokens", 0)
        if not tools:
            lines.append(f"  {d}: no data")
            continue
        lines.append(f"  {d}: {len(tools)} tools, ~{savings:,} tokens saved")
        for tname, tstats in sorted(tools.items()):
            lines.append(f"    {tname}: {tstats['calls']} calls, {tstats.get('avg_latency_ms', 0)}ms avg, "
                         f"{tstats['errors']} errors, ~{tstats.get('est_saved_tokens', 0):,} tokens saved")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
@_instrument_tool("compact_change_intelligence")
def compact_change_intelligence(
    project_path: str,
    staged: bool = False,
    unstaged: bool = True,
    respect_hygiene: bool = True,
) -> str:
    """Get compact, structured summary of git changes.

    Produces a low-token change intelligence payload suitable for downstream
    commit drafting. Applies repository hygiene filters by default to exclude
    noise paths (build artifacts, lock files, vendored deps, binaries, etc.).

    Args:
        project_path: Path to the git repository
        staged: Include staged changes
        unstaged: Include unstaged changes (default True)
        respect_hygiene: Filter out noise paths (default True)

    Returns:
        Compact JSON with changed files, change types, and intent cues
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    intel = CompactChangeIntel(path)
    cc = intel.summarize_working_changes(staged=staged, unstaged=unstaged, respect_hygiene=respect_hygiene)

    if cc.change_count == 0:
        return "No changes detected."

    return cc.to_json()


@mcp.tool()
@_instrument_tool("draft_commit")
def draft_commit(project_path: str) -> str:
    """Generate a local commit draft from working tree changes.

    Produces candidate commit message + rationale + confidence score.
    Final commit requires explicit approval via approve_commit_draft.

    Args:
        project_path: Path to the git repository

    Returns:
        Draft commit with message, rationale, and confidence
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    intel = CompactChangeIntel(path)
    cc = intel.summarize_working_changes()

    if cc.change_count == 0:
        return "No changes to commit."

    cfg = _get_config()
    generator = CommitGenerator(
        CommitGeneratorConfig(
            local_model=cfg.commit_model,
            remote_model=cfg.openrouter_commit_model,
            temperature=cfg.openrouter.temperature,
            max_tokens=cfg.openrouter.max_tokens,
            router=_get_llm_router(),
        )
    )
    draft = generator.generate(cc)

    gate = get_commit_gate()
    gate.reject()  # reset gate for new draft

    return (
        f"Draft commit message:\n{draft.message}\n\n"
        f"Rationale: {draft.rationale}\n"
        f"Confidence: {draft.confidence}\n"
        f"Source: {draft.source}\n\n"
        "Use approve_commit_draft to approve or provide an edited message."
    )


@mcp.tool()
@_instrument_tool("approve_commit_draft")
def approve_commit_draft(project_path: str, message: Optional[str] = None) -> str:
    """Approve or edit the pending commit draft and execute the commit.

    Args:
        project_path: Path to the git repository
        message: Optional edited message. If omitted, the draft message is used as-is.

    Returns:
        Commit result or gate status
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    gate = get_commit_gate()
    if gate.state == CommitGate.PENDING:
        return "No pending draft. Run draft_commit first."

    gate.approve(message)
    result = _execute_commit(path)
    return result


def _execute_commit(repo_path: Path) -> str:
    import subprocess

    gate = get_commit_gate()
    if not gate.can_commit:
        return "Commit not approved."

    msg = gate._approved_message or "(no message)"
    try:
        with open(repo_path / ".git/COMMIT_EDITMSG", "w") as f:
            f.write(msg)
        add = subprocess.run(
            ["git", "add", "-A"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=30,
        )
        if add.returncode != 0:
            return f"git add failed:\n{add.stderr or add.stdout}"
        result = subprocess.run(
            ["git", "commit", "--file", ".git/COMMIT_EDITMSG"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=30,
        )
        if result.returncode == 0:
            gate.reject()  # reset for next cycle
            return f"Commit successful:\n{result.stdout}"
        else:
            return f"Commit failed:\n{result.stderr or result.stdout}"
    except Exception as e:
        return f"Error: {e}"


def main():
    """Run the MCP server."""
    import os

    # Add src to path
    src_path = Path(__file__).parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    mcp.run()


if __name__ == "__main__":
    main()
