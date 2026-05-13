"""Disk-based cache for AST trees and file analyses."""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

from analyzers.base import FileAnalysis, Symbol


class Cache:
    """Disk-based cache for file analyses."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path.home() / ".code-context-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, file_path: Path) -> str:
        """Generate cache key from file path."""
        return hashlib.md5(str(file_path.resolve()).encode()).hexdigest()

    def _get_cache_file(self, file_path: Path) -> Path:
        """Get cache file path for a given file."""
        key = self._get_cache_key(file_path)
        return self.cache_dir / f"{key}.json"

    def get(self, file_path: Path) -> Optional[FileAnalysis]:
        """Get cached analysis if valid."""
        cache_file = self._get_cache_file(file_path)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r") as f:
                data = json.load(f)

            # Check if file has been modified
            if data.get("mtime", 0) != file_path.stat().st_mtime:
                return None

            # Check if cache is older than 24 hours
            if time.time() - data.get("timestamp", 0) > 86400:
                return None

            return self._deserialize(data)
        except Exception:
            return None

    def put(self, file_path: Path, analysis: FileAnalysis):
        """Cache an analysis result."""
        cache_file = self._get_cache_file(file_path)
        data = self._serialize(analysis)
        data["mtime"] = file_path.stat().st_mtime
        data["timestamp"] = time.time()

        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)

    def invalidate(self, file_path: Path):
        """Invalidate cache for a file."""
        cache_file = self._get_cache_file(file_path)
        if cache_file.exists():
            cache_file.unlink()

    def clear(self):
        """Clear all cached data."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

    def _serialize(self, analysis: FileAnalysis) -> dict:
        """Serialize FileAnalysis to dict."""
        return {
            "file_path": analysis.file_path,
            "language": analysis.language,
            "total_lines": analysis.total_lines,
            "summary": analysis.summary,
            "imports": analysis.imports,
            "dependencies": analysis.dependencies,
            "symbols": [self._serialize_symbol(sym) for sym in analysis.symbols],
        }

    def _serialize_symbol(self, sym: Symbol) -> dict:
        """Serialize Symbol to dict."""
        return {
            "name": sym.name,
            "type": sym.type,
            "start_line": sym.start_line,
            "end_line": sym.end_line,
            "doc_comment": sym.doc_comment,
            "parameters": sym.parameters,
            "return_type": sym.return_type,
            "children": [self._serialize_symbol(child) for child in sym.children],
        }

    def _deserialize(self, data: dict) -> FileAnalysis:
        """Deserialize dict to FileAnalysis."""
        symbols = [self._deserialize_symbol(sym_data) for sym_data in data.get("symbols", [])]
        return FileAnalysis(
            file_path=data["file_path"],
            language=data["language"],
            total_lines=data["total_lines"],
            symbols=symbols,
            imports=data.get("imports", []),
            dependencies=data.get("dependencies", []),
            summary=data.get("summary", ""),
        )

    def _deserialize_symbol(self, data: dict) -> Symbol:
        """Deserialize dict to Symbol."""
        children = [self._deserialize_symbol(child_data) for child_data in data.get("children", [])]
        return Symbol(
            name=data["name"],
            type=data["type"],
            start_line=data["start_line"],
            end_line=data["end_line"],
            doc_comment=data.get("doc_comment"),
            parameters=data.get("parameters"),
            return_type=data.get("return_type"),
            children=children,
        )
