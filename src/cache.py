"""Disk-based cache with version-aware keys, invalidation, and semantic summary support."""

import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from analyzers.base import FileAnalysis, SemanticSummary, Symbol

ANALYZER_VERSION = "1.0.0"
SUMMARY_MODEL_VERSION = "1.0.0"
CACHE_MAX_ENTRIES = 1000
MAX_SUMMARY_ENTRIES = 5000
STALE_DAYS = 7


def _file_hash(file_path: Path) -> str:
    """SHA-256 hash of file content for change detection."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class Cache:
    """Disk-based cache for file analyses and semantic summaries."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path.home() / ".code-context-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._summary_dir = self.cache_dir / "summaries"
        self._summary_dir.mkdir(parents=True, exist_ok=True)

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(raw: str) -> str:
        return hashlib.md5(raw.encode()).hexdigest()

    def _analysis_path(self, file_path: Path) -> Path:
        return self.cache_dir / f"{self._cache_key(str(file_path.resolve()))}.json"

    def _summary_cache_key(self, symbol_id: str, file_hash: str) -> str:
        return self._cache_key(f"{symbol_id}|{file_hash}|{ANALYZER_VERSION}|{SUMMARY_MODEL_VERSION}")

    def _summary_path(self, symbol_id: str, file_hash: str) -> Path:
        return self._summary_dir / f"{self._summary_cache_key(symbol_id, file_hash)}.json"

    # ── file analysis cache ──────────────────────────────────────────────

    def get(self, file_path: Path) -> Optional[FileAnalysis]:
        """Get cached analysis if valid (mtime check + staleness)."""
        cache_file = self._analysis_path(file_path)
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            if data.get("mtime", 0) != file_path.stat().st_mtime:
                return None
            if time.time() - data.get("timestamp", 0) > STALE_DAYS * 86400:
                return None
            if data.get("analyzer_version") != ANALYZER_VERSION:
                return None
            return self._deserialize(data)
        except Exception:
            return None

    def put(self, file_path: Path, analysis: FileAnalysis):
        """Cache an analysis result with version metadata."""
        cache_file = self._analysis_path(file_path)
        data = self._serialize(analysis)
        data["mtime"] = file_path.stat().st_mtime
        data["file_hash"] = _file_hash(file_path)
        data["timestamp"] = time.time()
        data["analyzer_version"] = ANALYZER_VERSION
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
        self._evict_if_needed()

    def invalidate(self, file_path: Path):
        """Invalidate analysis and any associated summaries for a file."""
        cache_file = self._analysis_path(file_path)
        if cache_file.exists():
            cache_file.unlink()

    def clear(self):
        """Clear all cached data."""
        for p in self.cache_dir.glob("*.json"):
            p.unlink()
        for p in self._summary_dir.glob("*.json"):
            p.unlink()

    # ── semantic summary cache ───────────────────────────────────────────

    def get_summary(self, symbol_id: str, file_hash: str) -> Optional[SemanticSummary]:
        """Get cached semantic summary if valid (version check)."""
        path = self._summary_path(symbol_id, file_hash)
        if not path.exists():
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            if data.get("analyzer_version") != ANALYZER_VERSION:
                return None
            if data.get("summary_model_version") != SUMMARY_MODEL_VERSION:
                return None
            if time.time() - data.get("timestamp", 0) > STALE_DAYS * 86400:
                return None
            return self._deserialize_summary(data)
        except Exception:
            return None

    def put_summary(self, symbol_id: str, file_hash: str, summary: SemanticSummary):
        """Cache a semantic summary with version metadata."""
        path = self._summary_path(symbol_id, file_hash)
        data = summary.to_dict()
        data["symbol_id"] = symbol_id
        data["file_hash"] = file_hash
        data["analyzer_version"] = ANALYZER_VERSION
        data["summary_model_version"] = SUMMARY_MODEL_VERSION
        data["timestamp"] = time.time()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._evict_summaries_if_needed()

    def invalidate_summaries_for_file(self, file_hash: str):
        """Remove all cached summaries referencing a given file hash."""
        count = 0
        for p in self._summary_dir.glob("*.json"):
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                if data.get("file_hash") == file_hash:
                    p.unlink()
                    count += 1
            except Exception:
                p.unlink()
                count += 1

    # ── eviction / bounds ────────────────────────────────────────────────

    def _evict_if_needed(self):
        files = sorted(self.cache_dir.glob("*.json"), key=os.path.getmtime)
        while len(files) > CACHE_MAX_ENTRIES:
            files[0].unlink()
            files = files[1:]

    def _evict_summaries_if_needed(self):
        files = sorted(self._summary_dir.glob("*.json"), key=os.path.getmtime)
        while len(files) > MAX_SUMMARY_ENTRIES:
            files[0].unlink()
            files = files[1:]

    def cleanup_stale(self):
        """Remove entries older than STALE_DAYS."""
        now = time.time()
        for p in self.cache_dir.glob("*.json"):
            if now - p.stat().st_mtime > STALE_DAYS * 86400:
                p.unlink()
        for p in self._summary_dir.glob("*.json"):
            if now - p.stat().st_mtime > STALE_DAYS * 86400:
                p.unlink()

    # ── serialization ────────────────────────────────────────────────────

    def _serialize(self, analysis: FileAnalysis) -> dict:
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
        d = {
            "name": sym.name,
            "type": sym.type,
            "start_line": sym.start_line,
            "end_line": sym.end_line,
            "doc_comment": sym.doc_comment,
            "parameters": sym.parameters,
            "return_type": sym.return_type,
            "children": [self._serialize_symbol(child) for child in sym.children],
        }
        if sym.semantic_summary:
            d["semantic_summary"] = sym.semantic_summary.to_dict()
        return d

    def _deserialize(self, data: dict) -> FileAnalysis:
        symbols = [self._deserialize_symbol(s) for s in data.get("symbols", [])]
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
        children = [self._deserialize_symbol(c) for c in data.get("children", [])]
        ss = None
        if "semantic_summary" in data:
            ss = self._deserialize_summary(data["semantic_summary"])
        return Symbol(
            name=data["name"],
            type=data["type"],
            start_line=data["start_line"],
            end_line=data["end_line"],
            doc_comment=data.get("doc_comment"),
            parameters=data.get("parameters"),
            return_type=data.get("return_type"),
            children=children,
            semantic_summary=ss,
        )

    @staticmethod
    def _deserialize_summary(data: dict) -> SemanticSummary:
        return SemanticSummary(
            summary_text=data.get("summary_text", ""),
            purpose=data.get("purpose", ""),
            behavior=data.get("behavior", ""),
            dependencies=data.get("dependencies", []),
            source=data.get("source", "heuristic"),
            confidence=data.get("confidence", 0.0),
            last_updated=data.get("last_updated"),
        )
