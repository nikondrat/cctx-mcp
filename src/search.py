"""Search functionality for finding symbols, files, and content in a project."""

import os
import re
from pathlib import Path
from typing import Optional

from analyzers import (
    GoAnalyzer,
    PythonAnalyzer,
    RustAnalyzer,
    SwiftAnalyzer,
    TypeScriptAnalyzer,
)
from analyzers.base import BaseAnalyzer, FileAnalysis, SemanticSummary, Symbol
from cache import Cache, _file_hash
from config import CodeContextConfig
from summaries import SemanticSummarizer

# Language extensions mapping
LANGUAGE_EXTENSIONS = {
    ".swift": SwiftAnalyzer,
    ".py": PythonAnalyzer,
    ".ts": TypeScriptAnalyzer,
    ".tsx": TypeScriptAnalyzer,
    ".js": TypeScriptAnalyzer,
    ".jsx": TypeScriptAnalyzer,
    ".rs": RustAnalyzer,
    ".go": GoAnalyzer,
}

# Directories to skip during traversal
SKIP_DIRS = frozenset({
    ".git", "node_modules", "Pods", "build", "dist", ".build",
    "__pycache__", "venv", ".venv", ".tox", "target", "DerivedData",
    ".xcodeproj", ".xcworkspace", ".swiftpm",
    "openspec",
})


class ProjectSearch:
    """Search and analyze files in a project."""

    def __init__(self, project_path: Path, cache: Optional[Cache] = None, config: Optional[CodeContextConfig] = None):
        self.project_path = project_path.resolve()
        self.cache = cache or Cache()
        self._analyzers: dict[str, BaseAnalyzer] = {}
        self._summarizer = SemanticSummarizer(self.cache)
        self._config = config or CodeContextConfig()

    @property
    def _feature_semantic_summaries(self) -> bool:
        return self._config.semantic_summaries_enabled

    def summarize_symbols(self, file_path: Path) -> Optional[list[SemanticSummary]]:
        """Generate semantic summaries for all symbols in a file."""
        analysis = self._analyze_file(file_path)
        if not analysis:
            return None
        if not self._feature_semantic_summaries:
            return None
        fh = _file_hash(file_path)
        return self._summarizer.summarize_file(analysis, fh)

    def get_analyzer(self, file_path: Path) -> Optional[BaseAnalyzer]:
        """Get appropriate analyzer for a file."""
        ext = file_path.suffix.lower()
        if ext not in LANGUAGE_EXTENSIONS:
            return None

        if ext not in self._analyzers:
            analyzer_class = LANGUAGE_EXTENSIONS[ext]
            self._analyzers[ext] = analyzer_class()

        return self._analyzers[ext]

    def smart_read(self, file_path: Path) -> Optional[str]:
        """Read a file and return compact analysis."""
        # Try cache first
        cached = self.cache.get(file_path)
        if cached:
            if self._feature_semantic_summaries:
                fh = _file_hash(file_path)
                self._summarizer.summarize_file(cached, fh)
            return cached.compact_output(include_summaries=self._feature_semantic_summaries)

        # Analyze file
        analyzer = self.get_analyzer(file_path)
        if not analyzer:
            return None

        analysis = analyzer.analyze(file_path)
        if not analysis:
            return None

        # Generate summaries if enabled
        if self._feature_semantic_summaries:
            fh = _file_hash(file_path)
            self._summarizer.summarize_file(analysis, fh)

        # Cache result
        self.cache.put(file_path, analysis)

        return analysis.compact_output(include_summaries=self._feature_semantic_summaries)

    def find_symbols(self, project_path: Optional[Path] = None, name: Optional[str] = None, symbol_type: Optional[str] = None) -> list[dict]:
        """Find symbols across the project."""
        search_path = project_path or self.project_path
        results = []

        for file_path in self._iter_source_files(search_path):
            analysis = self._analyze_file(file_path)
            if not analysis:
                continue

            for sym in self._collect_all_symbols(analysis.symbols):
                if name and name.lower() not in sym.name.lower():
                    continue
                if symbol_type and sym.type != symbol_type:
                    continue

                results.append({
                    "file": str(file_path.relative_to(self.project_path)),
                    "name": sym.name,
                    "type": sym.type,
                    "line": sym.start_line,
                    "doc_comment": sym.doc_comment,
                })

        return results

    def get_dependencies(self, file_path: Path) -> Optional[list[str]]:
        """Get dependencies of a file."""
        cached = self.cache.get(file_path)
        if cached:
            return cached.dependencies

        analyzer = self.get_analyzer(file_path)
        if not analyzer:
            return None

        analysis = analyzer.analyze(file_path)
        if not analysis:
            return None

        self.cache.put(file_path, analysis)
        return analysis.dependencies

    def trace_calls(self, symbol_name: str, project_path: Optional[Path] = None) -> list[dict]:
        """Find where a symbol is called/used."""
        search_path = project_path or self.project_path
        results = []

        # Search for symbol definition first
        definitions = self.find_symbols(search_path, name=symbol_name)
        if not definitions:
            return results

        # Now search for usages in other files
        for file_path in self._iter_source_files(search_path):
            # Skip files where symbol is defined
            if any(d["file"] == str(file_path.relative_to(self.project_path)) for d in definitions):
                continue

            # Read file content and search for symbol name
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                if symbol_name in content:
                    # Find line numbers where symbol appears
                    for i, line in enumerate(content.splitlines(), 1):
                        if symbol_name in line:
                            results.append({
                                "file": str(file_path.relative_to(self.project_path)),
                                "line": i,
                                "context": line.strip()[:100],
                            })
            except Exception:
                continue

        return results

    def _analyze_file(self, file_path: Path) -> Optional[FileAnalysis]:
        """Analyze a single file with caching."""
        cached = self.cache.get(file_path)
        if cached:
            return cached

        analyzer = self.get_analyzer(file_path)
        if not analyzer:
            return None

        analysis = analyzer.analyze(file_path)
        if analysis:
            self.cache.put(file_path, analysis)

        return analysis

    def _collect_all_symbols(self, symbols: list[Symbol]) -> list[Symbol]:
        """Recursively collect all symbols including children."""
        result = []
        for sym in symbols:
            result.append(sym)
            result.extend(self._collect_all_symbols(sym.children))
        return result

    def _iter_source_files(self, path: Path):
        """Iterate over source files in a directory."""
        if not path.exists():
            return

        for root, dirs, files in os.walk(path):
            # Skip hidden directories and common non-source directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "Pods", "build", "dist", ".git", "__pycache__", "venv", ".venv")]

            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in LANGUAGE_EXTENSIONS:
                    yield file_path

    # ─── code_search: grep replacement ───────────────────────────────────

    def code_search(
        self,
        pattern: str,
        *,
        use_regex: bool = False,
        file_pattern: Optional[str] = None,
        case_sensitive: bool = False,
        context_lines: int = 2,
        max_results: int = 100,
    ) -> list[dict]:
        """Search file contents for a pattern (grep replacement).

        Args:
            pattern: Text or regex pattern to search for
            use_regex: Treat pattern as a regex
            file_pattern: Glob pattern to filter files (e.g. "*.swift", "**/*Interactor*")
            case_sensitive: Case-sensitive search
            context_lines: Number of context lines before/after each match
            max_results: Maximum number of matches to return

        Returns:
            List of dicts with file, line, text, and context
        """
        flags = 0 if case_sensitive else re.IGNORECASE
        if use_regex:
            try:
                compiled = re.compile(pattern, flags)
            except re.error:
                return [{"error": f"Invalid regex: {pattern}"}]
            match_fn = lambda line: compiled.search(line)
        else:
            if case_sensitive:
                match_fn = lambda line: pattern in line
            else:
                lower_pattern = pattern.lower()
                match_fn = lambda line: lower_pattern in line.lower()

        results = []
        for file_path in self._iter_all_files(self.project_path, file_pattern):
            if len(results) >= max_results:
                break
            try:
                lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                continue

            for i, line in enumerate(lines):
                if match_fn(line):
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    context = []
                    for j in range(start, end):
                        prefix = "  " if j != i else "▶ "
                        context.append(f"{j+1}:{prefix}{lines[j]}")

                    results.append({
                        "file": str(file_path.relative_to(self.project_path)),
                        "line": i + 1,
                        "text": line.strip(),
                        "context": "\n".join(context),
                    })
                    if len(results) >= max_results:
                        break

        return results

    # ─── find_files: find replacement ────────────────────────────────────

    def find_files(
        self,
        name_pattern: Optional[str] = None,
        extension: Optional[str] = None,
        path_contains: Optional[str] = None,
        max_depth: Optional[int] = None,
        max_results: int = 100,
    ) -> list[dict]:
        """Find files by name, extension, or path pattern (find replacement).

        Args:
            name_pattern: Glob pattern for filename (e.g. "*Interactor*", "*.swift")
            extension: File extension to filter (e.g. "swift", "py") — without dot
            path_contains: Substring that must appear in the relative path
            max_depth: Maximum directory depth to search
            max_results: Maximum number of results

        Returns:
            List of dicts with short relative path, size, and modification time
        """
        results = []
        for file_path in self._iter_all_files(self.project_path, name_pattern, max_depth):
            if len(results) >= max_results:
                break

            rel = file_path.relative_to(self.project_path)
            rel_str = str(rel)

            if extension and file_path.suffix.lstrip(".") != extension:
                continue
            if path_contains and path_contains.lower() not in rel_str.lower():
                continue

            try:
                stat = file_path.stat()
                size = stat.st_size
                mtime = stat.st_mtime
            except Exception:
                size = 0
                mtime = 0

            results.append({
                "path": rel_str,
                "size_kb": round(size / 1024, 1),
                "lines": self._count_lines_safe(file_path),
                "modified": self._format_mtime(mtime),
            })

        return results

    # ─── dir_summary: ls -la replacement ─────────────────────────────────

    def dir_summary(
        self,
        dir_path: Optional[str] = None,
        depth: int = 1,
    ) -> str:
        """Summarize a directory's structure (ls -la replacement).

        Args:
            dir_path: Relative path within project (or None for root)
            depth: How many levels deep to show subdirectories

        Returns:
            Structured summary with subdirectories, file counts by type, and total size
        """
        target = self.project_path / dir_path if dir_path else self.project_path
        if not target.is_dir():
            return f"Error: Directory not found: {dir_path or '(project root)'}"

        return self._build_dir_summary(target, self.project_path, depth, prefix="")

    def _build_dir_summary(
        self,
        directory: Path,
        project_root: Path,
        depth: int,
        prefix: str,
    ) -> str:
        """Recursively build directory summary."""
        rel = directory.relative_to(project_root)
        lines = [f"📁 {rel}/" if rel != Path(".") else f"📁 {project_root.name}/"]

        try:
            entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            lines.append("  (permission denied)")
            return "\n".join(lines)

        # Group by type
        subdirs = []
        files_by_ext: dict[str, list[Path]] = {}
        total_size = 0

        for entry in entries:
            if entry.name.startswith(".") or entry.name in SKIP_DIRS:
                continue
            if entry.is_dir():
                subdirs.append(entry)
            elif entry.is_file():
                ext = entry.suffix.lower() or "(no ext)"
                files_by_ext.setdefault(ext, []).append(entry)
                try:
                    total_size += entry.stat().st_size
                except Exception:
                    pass

        # Show subdirectories
        for sd in subdirs:
            sd_rel = sd.relative_to(project_root)
            sd_files = sum(1 for _ in self._iter_all_files(sd, max_depth=1))
            lines.append(f"  📂 {sd.name}/  ({sd_files} source files)")
            if depth > 1:
                sub_summary = self._build_dir_summary(sd, project_root, depth - 1, prefix + "  ")
                # Indent sub-summary lines
                for sub_line in sub_summary.split("\n")[1:]:  # skip header
                    lines.append(f"    {sub_line}")

        # Show file type summary
        if files_by_ext:
            lines.append("")
            lines.append("  Files by type:")
            for ext, files in sorted(files_by_ext.items(), key=lambda x: -len(x[1])):
                ext_size = sum(f.stat().st_size for f in files if f.exists())
                lines.append(f"    {ext}: {len(files)} files  ({ext_size / 1024:.0f} KB)")

        lines.append(f"  Total size: {total_size / 1024:.0f} KB")
        return "\n".join(lines)

    # ─── helpers ─────────────────────────────────────────────────────────

    def _iter_all_files(
        self,
        path: Path,
        name_pattern: Optional[str] = None,
        max_depth: Optional[int] = None,
    ):
        """Iterate over all files (not just source files) with optional filtering."""
        if not path.exists():
            return

        base_depth = len(path.relative_to(self.project_path).parts) if path != self.project_path else 0

        for root, dirs, files in os.walk(path):
            current = Path(root)
            rel = current.relative_to(self.project_path)
            current_depth = len(rel.parts)

            if max_depth is not None and current_depth - base_depth >= max_depth:
                dirs.clear()
                continue

            # Skip ignored directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
            dirs.sort()

            for file in sorted(files):
                file_path = current / file
                if name_pattern and not self._match_glob(file, name_pattern):
                    continue
                yield file_path

    @staticmethod
    def _match_glob(filename: str, pattern: str) -> bool:
        """Simple glob matching supporting * and **."""
        if "**" in pattern:
            # ** matches any path segments — use regex
            regex = pattern.replace("**/", "(.+/)?").replace("**", ".*").replace("*", "[^/]*")
            return bool(re.match(f"^{regex}$", filename))
        if "*" in pattern:
            regex = pattern.replace("*", ".*")
            return bool(re.match(f"^{regex}$", filename))
        return filename == pattern

    @staticmethod
    def _count_lines_safe(file_path: Path) -> int:
        """Count lines in a file, returning 0 on error."""
        try:
            with open(file_path, "rb") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    @staticmethod
    def _format_mtime(mtime: float) -> str:
        """Format modification time as relative string."""
        import time
        diff = time.time() - mtime
        if diff < 60:
            return "just now"
        if diff < 3600:
            return f"{int(diff // 60)}m ago"
        if diff < 86400:
            return f"{int(diff // 3600)}h ago"
        if diff < 604800:
            return f"{int(diff // 86400)}d ago"
        return time.strftime("%Y-%m-%d", time.localtime(mtime))
