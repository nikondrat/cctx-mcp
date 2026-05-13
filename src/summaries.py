"""Lazy semantic summary generation with provenance/confidence."""

from datetime import datetime, timezone
from typing import Optional

from analyzers.base import FileAnalysis, SemanticSummary, Symbol
from cache import Cache


class SemanticSummarizer:
    """Generates semantic summaries for symbols on demand (lazy)."""

    def __init__(self, cache: Cache):
        self._cache = cache

    def summarize_symbol(
        self, symbol: Symbol, file_hash: str, dependencies: list[str]
    ) -> SemanticSummary:
        """Generate a semantic summary for a single symbol (lazy)."""
        symbol_id = self._symbol_id(symbol)
        cached = self._cache.get_summary(symbol_id, file_hash)
        if cached:
            return cached

        summary = self._build_summary(symbol, dependencies)
        self._cache.put_summary(symbol_id, file_hash, summary)
        return summary

    def summarize_file(
        self, analysis: FileAnalysis, file_hash: str
    ) -> list[SemanticSummary]:
        """Generate summaries for all symbols in a file."""
        summaries = []
        for sym in analysis.symbols:
            ss = self.summarize_symbol(sym, file_hash, analysis.dependencies)
            sym.semantic_summary = ss
            summaries.append(ss)
            for child in self._collect_children(sym):
                child_ss = self.summarize_symbol(child, file_hash, analysis.dependencies)
                child.semantic_summary = child_ss
                summaries.append(child_ss)
        return summaries

    # ── internals ────────────────────────────────────────────────────────

    @staticmethod
    def _symbol_id(symbol: Symbol) -> str:
        return f"{symbol.type}:{symbol.name}:{symbol.start_line}"

    @staticmethod
    def _collect_children(symbol: Symbol) -> list[Symbol]:
        result = []
        for child in symbol.children:
            result.append(child)
            result.extend(SemanticSummarizer._collect_children(child))
        return result

    def _build_summary(self, symbol: Symbol, dependencies: list[str]) -> SemanticSummary:
        now = datetime.now(timezone.utc).isoformat()
        name = symbol.name
        sym_type = symbol.type
        doc = symbol.doc_comment or ""
        params = symbol.parameters or ""
        ret = symbol.return_type or ""

        if doc:
            purpose = self._extract_purpose_from_doc(doc, name)
            behavior = doc
            source = "doc"
            confidence = 0.8
        elif sym_type in ("class", "struct", "enum", "interface", "protocol"):
            purpose = f"Defines the {name} {sym_type}"
            behavior = self._infer_behavior_from_children(symbol)
            source = "heuristic"
            confidence = 0.5
        elif sym_type in ("function", "method", "init"):
            purpose = self._infer_purpose_from_name(name)
            behavior = f"{sym_type} {name}({params})"
            if ret:
                behavior += f" → {ret}"
            if doc:
                behavior += f". {doc}"
            source = "heuristic"
            confidence = 0.5
        else:
            purpose = f"Symbol {name}"
            behavior = f"{sym_type} {name}"
            source = "heuristic"
            confidence = 0.2

        summary_text = f"{purpose}. {behavior}" if purpose != behavior else purpose

        return SemanticSummary(
            summary_text=summary_text,
            purpose=purpose,
            behavior=behavior,
            dependencies=dependencies,
            source=source,
            confidence=confidence,
            last_updated=now,
        )

    @staticmethod
    def _extract_purpose_from_doc(doc: str, name: str) -> str:
        first = doc.split(".")[0].strip()
        if len(first) > 120:
            first = first[:117] + "..."
        return first

    @staticmethod
    def _infer_purpose_from_name(name: str) -> str:
        prefixes = {
            "get": "Retrieves",
            "set": "Sets",
            "is": "Checks whether",
            "has": "Checks whether",
            "find": "Finds",
            "search": "Searches for",
            "create": "Creates",
            "update": "Updates",
            "delete": "Deletes",
            "remove": "Removes",
            "add": "Adds",
            "parse": "Parses",
            "build": "Builds",
            "validate": "Validates",
            "format": "Formats",
            "convert": "Converts",
            "load": "Loads",
            "save": "Saves",
            "fetch": "Fetches",
            "compute": "Computes",
            "calculate": "Calculates",
        }
        for prefix, verb in prefixes.items():
            if name.lower().startswith(prefix):
                rest = name[len(prefix):]
                rest = rest.lstrip("_")
                return f"{verb} {rest}" if rest else verb
        return name.replace("_", " ").capitalize()

    @staticmethod
    def _infer_behavior_from_children(symbol: Symbol) -> str:
        if not symbol.children:
            return f"{symbol.type} {symbol.name}"
        method_names = [c.name for c in symbol.children[:5]]
        methods = ", ".join(method_names)
        rest = f" +{len(symbol.children) - 5} more" if len(symbol.children) > 5 else ""
        return f"{symbol.type} {symbol.name} with methods: {methods}{rest}"
