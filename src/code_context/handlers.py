"""All MCP tool implementations — no server decorators, pure logic."""

import importlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Optional

from code_context.cache import Cache, _file_hash
from code_context.change_intel import CompactChangeIntel, CommitGate
from code_context.commit_generator import CommitGenerator, CommitGeneratorConfig
from code_context.config import CodeContextConfig
from code_context.context import set_tool_baseline
from code_context.llm.providers.ollama import OllamaProvider
from code_context.llm.providers.openrouter import OpenRouterProvider
from code_context.llm.router import LLMRouter
from code_context.metrics import get_metrics
from code_context.search import ProjectSearch, LANGUAGE_EXTENSIONS
from code_context.summaries import SemanticSummarizer
from code_context.vector_index import VectorIndex

_cache: Optional[Cache] = None
_searches: dict[str, ProjectSearch] = {}
_vector_indexes: dict[str, VectorIndex] = {}
_llm_router: Optional[LLMRouter] = None
_commit_gate: Optional[CommitGate] = None


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
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache


def get_search(project_path: str) -> ProjectSearch:
    if project_path not in _searches:
        _searches[project_path] = ProjectSearch(Path(project_path), get_cache())
    return _searches[project_path]


def get_commit_gate() -> CommitGate:
    global _commit_gate
    if _commit_gate is None:
        _commit_gate = CommitGate()
    return _commit_gate


def tool_smart_read(file_path: str, project_path: Optional[str] = None) -> str:
    """Structured file analysis: symbol hierarchy, dependencies, line ranges, doc comments.

    Use INSTEAD of Read/cat when exploring a file you haven't seen before.
    ~87% token savings vs reading entire file.

    Only fall back to Read when you need the full implementation body to make an edit.
    Even then, call smart_read first to find exact line ranges.

    Args:
        file_path: Path to the file to analyze
        project_path: Optional project root for richer context (import resolution, etc.)
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"

        if path.exists():
            baseline = max(100, path.stat().st_size // 4)
            set_tool_baseline(baseline=baseline, baseline_op="read_file")

        if project_path:
            search = get_search(project_path)
        else:
            search = ProjectSearch(path.parent, get_cache())

        result = search.smart_read(path)
        if result is None:
            ext = path.suffix.lower()
            return f"Error: Could not analyze {ext} files — missing or unsupported analyzer for '{file_path}'"

        return result
    except Exception as e:
        return f"Error: smart_read failed for '{file_path}': {e}"


def tool_find_symbols(project_path: str, name: Optional[str] = None, symbol_type: Optional[str] = None) -> str:
    """Exact symbol search by name or type across the project.

    Use INSTEAD of grep to find function/class/method/interface/struct/enum definitions.
    ~99% token savings vs grep + read to find what you need.

    Args:
        project_path: Root directory of the project
        name: Optional symbol name to search for (partial match)
        symbol_type: Optional filter: function, class, method, interface, struct, enum, protocol
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    search = get_search(project_path)
    results = search.find_symbols(path, name=name, symbol_type=symbol_type)

    set_tool_baseline(baseline=len(results) * 200, baseline_op="grep+read")

    if not results:
        return "No symbols found matching criteria."

    output = [f"Found {len(results)} symbols:"]
    for r in results:
        line = f"  {r['file']}:{r['line']} - {r['type']} {r['name']}"
        if r.get("doc_comment"):
            line += f" // {r['doc_comment']}"
        output.append(line)

    return "\n".join(output)


def tool_get_dependencies(file_path: str, project_path: Optional[str] = None) -> str:
    """All imports/dependencies of a file without reading its contents.

    Use INSTEAD of Read + manual import parsing to understand a file's dependencies.
    ~96% token savings vs reading the file and extracting imports manually.

    Args:
        file_path: Path to the source file
        project_path: Optional project root for import resolution
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

    set_tool_baseline(baseline=max(100, path.stat().st_size // 4), baseline_op="read_file")

    if not deps:
        return "No dependencies found."

    return f"Dependencies for {file_path}:\n" + "\n".join(f"  - {dep}" for dep in deps)


def tool_trace_calls(symbol_name: str, project_path: str) -> str:
    """Every call site of a symbol across the project. Impact analysis.

    Use INSTEAD of grep to find all usages before refactoring a function/class.
    ~90% token savings vs grep + manual context reading.

    Call BEFORE changing any shared symbol to understand impact radius.

    Args:
        symbol_name: Fully qualified or bare symbol name to trace
        project_path: Root directory of the project
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    search = get_search(project_path)
    results = search.trace_calls(symbol_name, path)

    set_tool_baseline(baseline=len(results) * 150, baseline_op="grep+read")

    if not results:
        return f"No usages found for symbol: {symbol_name}"

    output = [f"Found {len(results)} usages of '{symbol_name}':"]
    for r in results:
        output.append(f"  {r['file']}:{r['line']} - {r['context']}")

    return "\n".join(output)


def tool_analyze_project(project_path: str, max_depth: int = 2) -> str:
    """Project-wide structure: file counts, languages, directory tree.

    Use INSTEAD of find/ls + manual counting to understand project layout.
    ~98% token savings vs walking the tree manually.

    Call when first entering a new project to get oriented.

    Args:
        project_path: Root directory of the project
        max_depth: Maximum directory tree depth to scan (default 2)
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    stats = {"files": 0, "languages": {}, "directories": 0}

    for root, dirs, files in os.walk(path):
        rel_path = Path(root).relative_to(path)
        if len(rel_path.parts) > max_depth:
            dirs.clear()
            continue

        stats["directories"] += 1

        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "Pods", "build", "dist", ".git", "__pycache__", "venv", ".venv")]

        for file in files:
            file_path = Path(root) / file
            ext = file_path.suffix.lower()
            if ext in LANGUAGE_EXTENSIONS:
                stats["files"] += 1
                lang = LANGUAGE_EXTENSIONS[ext].__name__.replace("Analyzer", "").lower()
                stats["languages"][lang] = stats["languages"].get(lang, 0) + 1

    set_tool_baseline(baseline=stats["directories"] * 200 + stats["files"] * 100, baseline_op="tree+walk")

    output = [f"Project: {project_path}"]
    output.append(f"Total source files: {stats['files']}")
    output.append(f"Directories scanned: {stats['directories']}")
    output.append("")
    output.append("Languages:")
    for lang, count in sorted(stats["languages"].items(), key=lambda x: x[1], reverse=True):
        output.append(f"  {lang}: {count} files")

    return "\n".join(output)


def tool_get_symbol_summaries(file_path: str, project_path: Optional[str] = None) -> str:
    """Semantic AI summaries per symbol: purpose, behavior, confidence, provenance.

    Use when you need to understand what a symbol DOES, not just where it is.
    ~90% token savings vs reading the entire implementation to infer purpose.

    Requires: LLM provider configured (Ollama or OpenRouter).

    Args:
        file_path: Path to the source file
        project_path: Optional project root for context
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


def tool_code_search(project_path: str, pattern: str, use_regex: bool = False, file_pattern: Optional[str] = None, case_sensitive: bool = False, context_lines: int = 2, max_results: int = 50) -> str:
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    search = get_search(project_path)
    results = search.code_search(pattern, use_regex=use_regex, file_pattern=file_pattern, case_sensitive=case_sensitive, context_lines=context_lines, max_results=max_results)

    output_len = sum(len(r.get("context", "")) for r in results) // 4
    set_tool_baseline(baseline=output_len + len(results) * 20, baseline_op="grep")

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


def tool_find_files(project_path: str, name_pattern: Optional[str] = None, extension: Optional[str] = None, path_contains: Optional[str] = None, max_depth: Optional[int] = None, max_results: int = 50) -> str:
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    search = get_search(project_path)
    results = search.find_files(name_pattern=name_pattern, extension=extension, path_contains=path_contains, max_depth=max_depth, max_results=max_results)

    set_tool_baseline(baseline=len(results) * 50, baseline_op="find+ls")

    if not results:
        return "No files found matching criteria."

    output = [f"Found {len(results)} files:"]
    for r in results:
        output.append(f"  {r['path']}  ({r['size_kb']} KB, {r['lines']} lines, {r['modified']})")

    return "\n".join(output)


def tool_dir_summary(project_path: str, dir_path: Optional[str] = None, depth: int = 1) -> str:
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    search = get_search(project_path)
    result = search.dir_summary(dir_path=dir_path, depth=depth)
    set_tool_baseline(baseline=len(result) * 2, baseline_op="ls")
    return result


def tool_semantic_search(query: str, project_path: str, top_k: int = 5) -> str:
    if not query or not query.strip():
        return "semantic_search: empty query."

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

    set_tool_baseline(baseline=len(results) * 1000, baseline_op="grep+read")

    if index.last_error:
        err = index.last_error
        if "ollama" in err.lower() or "provider" in err.lower():
            return f"semantic_search unavailable.\n  Reason: {err}\n  Fix: ensure Ollama is running (ollama serve) and nomic-embed-text is installed (ollama pull nomic-embed-text).\n  Alternative: use find_symbols or code_search."
        return f"semantic_search error: {err}"

    if not results:
        return "No results found. Try re-indexing or using find_symbols."

    lines = [f"Top {len(results)} results for: {query!r}\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.file}:{r.line}  [{r.symbol}]  score={r.score}")
        lines.append(f"   {r.snippet[:80].replace(chr(10), ' ')}")
        lines.append("")
    return "\n".join(lines)


def tool_get_config() -> str:
    """Current feature flags and provider settings for code-context.

    Use to check which LLM providers, embedding models, and features are enabled.
    Call before using features that depend on LLM (summaries, commits, embeddings).
    Not a replacement for a native operation — configuration introspection.
    """
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

def tool_get_health() -> str:
    """System dependency health: Ollama, embeddings, vector index, tree-sitter.

    Use to diagnose why a code-context feature isn't working.
    Call when semantic_search or LLM-dependent tools return errors.
    Not a replacement for a native operation — diagnostics.
    """
    cfg = _get_config()
    report: dict[str, Any] = {}

    ollama_status: dict[str, Any] = {}
    try:
        req = urllib.request.Request(f"{cfg.ollama.base_url}/api/tags", method="GET")
        started = time.perf_counter()
        with urllib.request.urlopen(req, timeout=2) as resp:
            lat = int((time.perf_counter() - started) * 1000)
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            ollama_status = {"status": "ok", "latency_ms": lat, "models": models}
    except (urllib.error.URLError, ConnectionError, OSError) as e:
        ollama_status = {"status": "error", "error": f"Ollama not running: {e}", "fix": "Run: ollama serve"}

    report["ollama"] = ollama_status

    emb_model = cfg.embed_model
    if ollama_status.get("status") == "ok":
        emb_found = any(emb_model in m or m.startswith(emb_model) for m in ollama_status.get("models", []))
        if emb_found:
            report["embedding_model"] = {"status": "ok", "model": emb_model}
        else:
            report["embedding_model"] = {"status": "error", "model": emb_model, "error": f"Model '{emb_model}' not found in Ollama", "fix": f"Run: ollama pull {emb_model}"}
    else:
        report["embedding_model"] = {"status": "unknown", "model": emb_model}

    vi_status: dict[str, Any] = {"status": "not_built"}
    if _vector_indexes:
        for proj, idx in _vector_indexes.items():
            if idx._chunks:
                vi_status = {"status": "ok", "chunks": len(idx._chunks), "project": proj}
                break
    report["vector_index"] = vi_status

    try:
        ts = importlib.import_module("tree_sitter")
        ts_ver = getattr(ts, "__version__", "installed")
        report["tree_sitter"] = {"status": "ok", "version": str(ts_ver)}
    except ImportError:
        report["tree_sitter"] = {"status": "error", "error": "tree_sitter not installed"}

    return json.dumps(report)


def tool_get_metrics_report() -> str:
    return get_metrics().report()


def tool_get_metrics_events(limit: int = 25) -> str:
    metrics = get_metrics()
    events = metrics.recent_events(limit=limit)
    if not events:
        return "No metrics events recorded yet."

    lines = [f"Recent metrics events ({len(events)}):"]
    for event in events:
        status = "ok" if event.get("ok") else "error"
        savings = event.get("savings_tokens", "")
        baseline = event.get("tokens_baseline", "")
        output = event.get("tokens_output", "")
        savings_str = f"savings={savings}" if savings != "" else ""
        tokens_str = f" base={baseline} out={output}" if baseline else ""
        lines.append(f"  ts={event.get('ts')} tool={event.get('tool')} {savings_str}{tokens_str} latency_ms={event.get('latency_ms')} status={status}")
    return "\n".join(lines)


def tool_get_metrics_slowest(limit: int = 5) -> str:
    metrics = get_metrics()
    tools = metrics.slowest(limit=limit)
    if not tools:
        return "No tool metrics recorded yet."

    lines = [f"Top {len(tools)} slowest tools:"]
    for t in tools:
        lines.append(f"  {t['tool']}: {t['calls']} calls, avg {t['avg_latency_ms']}ms, total {t['total_latency_ms']}ms, errors {t['errors']}")
    return "\n".join(lines)


def tool_get_metrics_errors() -> str:
    metrics = get_metrics()
    summary = metrics.errors_summary()
    if not summary["tools_with_errors"]:
        return "No errors recorded across any tool."

    lines = [f"Error summary ({summary['total_errors']}/{summary['total_calls']} calls, {summary['error_rate']:.2%}):"]
    for t in summary["tools_with_errors"]:
        lines.append(f"  {t['tool']}: {t['errors']} errors / {t['calls']} calls")
    return "\n".join(lines)


def tool_reset_metrics() -> str:
    return get_metrics().reset()


def tool_get_metrics_daily_trend(days: int = 7) -> str:
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
            lines.append(f"    {tname}: {tstats['calls']} calls, {tstats.get('avg_latency_ms', 0)}ms avg, {tstats['errors']} errors, ~{tstats.get('est_saved_tokens', 0):,} tokens saved{', real' if not tstats.get('is_estimate') else ', estimate'}")
        lines.append("")
    return "\n".join(lines)


def tool_compact_change_intelligence(project_path: str, staged: bool = False, unstaged: bool = True, respect_hygiene: bool = True) -> str:
    """Structured diff + intent cues. Replaces git diff + git status.

    Use INSTEAD of git diff/git status to understand working changes before committing.
    ~75% token savings vs raw diff output.

    Call BEFORE draft_commit to review what will be committed.

    Args:
        project_path: Git repository root
        staged: Include staged changes (default False)
        unstaged: Include unstaged changes (default True)
        respect_hygiene: Skip generated files, lockfiles, etc. (default True)
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    intel = CompactChangeIntel(path)
    cc = intel.summarize_working_changes(staged=staged, unstaged=unstaged, respect_hygiene=respect_hygiene)

    if cc.change_count == 0:
        return "No changes detected."

    raw_diff_size = len(cc.to_json()) * 4
    set_tool_baseline(baseline=raw_diff_size, baseline_op="git_diff")
    return cc.to_json()


def tool_draft_commit(project_path: str) -> str:
    """AI-generated conventional commit message from working changes.

    Use INSTEAD of writing commit messages from scratch.
    ~90% token savings vs manual message drafting.

    Always call compact_change_intelligence first, then review the draft
    before calling approve_commit_draft.

    Args:
        project_path: Git repository root
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    intel = CompactChangeIntel(path)
    cc = intel.summarize_working_changes(staged=True, unstaged=False)

    if cc.change_count == 0:
        return "No staged changes to commit."

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
    gate.reject()

    return f"Draft commit message:\n{draft.message}\n\nRationale: {draft.rationale}\nConfidence: {draft.confidence}\nSource: {draft.source}\n\nUse approve_commit_draft to approve or provide an edited message."


def tool_approve_commit_draft(project_path: str, message: Optional[str] = None) -> str:
    """Execute git commit after reviewing draft.

    Use INSTEAD of git add + git commit. Enforces the draft-review cycle.
    Combined with draft_commit, replaces the entire manual commit flow.

    Pass a custom message to override the draft. Omit to use the generated draft.

    Args:
        project_path: Git repository root
        message: Optional custom commit message (uses draft if omitted)
    """
    path = Path(project_path)
    if not path.exists():
        return f"Error: Project not found: {project_path}"

    gate = get_commit_gate()
    if gate.state == CommitGate.PENDING:
        return "No pending draft. Run draft_commit first."

    gate.approve(message)
    return _execute_commit(path)


def tool_list_tools() -> str:
    """List all available cctx MCP tools with descriptions."""
    return """cctx MCP tools:

  File Analysis
    smart_read          — Structured file analysis (symbols, deps, doc comments)
    get_dependencies    — All imports/dependencies of a file
    get_symbol_summaries — AI semantic summaries per symbol

  Search & Navigation
    find_symbols        — Find symbols by name or type across project
    trace_calls         — Every call site of a symbol (impact analysis)
    analyze_project     — Project structure: files, languages, directory tree

  Git & Commits
    compact_change_intelligence — Structured diff + status (replaces git diff)
    draft_commit        — AI commit message from working changes
    approve_commit_draft — Execute the approved commit

  System
    get_config          — Feature flags and provider settings
    get_health          — Dependency health (Ollama, tree-sitter, etc.)
    get_version         — Server version and build info
    list_tools          — This list
"""


def _execute_commit(repo_path: Path) -> str:
    import subprocess

    gate = get_commit_gate()
    if not gate.can_commit:
        return "Commit not approved."

    msg = gate._approved_message or "(no message)"
    try:
        with open(repo_path / ".git/COMMIT_EDITMSG", "w") as f:
            f.write(msg)
        result = subprocess.run(
            ["git", "commit", "--file", ".git/COMMIT_EDITMSG"],
            capture_output=True, text=True, cwd=repo_path, timeout=30,
        )
        if result.returncode == 0:
            gate.reject()
            return f"Commit successful:\n{result.stdout}"
        else:
            return f"Commit failed:\n{result.stderr or result.stdout}"
    except Exception as e:
        return f"Error: {e}"
