"""Search functionality for finding symbols and files in a project."""

import os
from pathlib import Path
from typing import Optional

from analyzers import (
    GoAnalyzer,
    PythonAnalyzer,
    RustAnalyzer,
    SwiftAnalyzer,
    TypeScriptAnalyzer,
)
from analyzers.base import BaseAnalyzer, FileAnalysis, Symbol
from cache import Cache

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


class ProjectSearch:
    """Search and analyze files in a project."""

    def __init__(self, project_path: Path, cache: Optional[Cache] = None):
        self.project_path = project_path.resolve()
        self.cache = cache or Cache()
        self._analyzers: dict[str, BaseAnalyzer] = {}

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
            return cached.compact_output()

        # Analyze file
        analyzer = self.get_analyzer(file_path)
        if not analyzer:
            return None

        analysis = analyzer.analyze(file_path)
        if not analysis:
            return None

        # Cache result
        self.cache.put(file_path, analysis)

        return analysis.compact_output()

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
