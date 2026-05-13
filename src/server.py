"""MCP Server for code-context - efficient code analysis for AI agents."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from cache import Cache
from search import ProjectSearch

# Create MCP server
mcp = FastMCP("code-context")

# Global cache and search instances
_cache: Optional[Cache] = None
_searches: dict[str, ProjectSearch] = {}


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
