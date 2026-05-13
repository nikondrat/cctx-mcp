"""Base analyzer interface for all language-specific analyzers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tree_sitter as ts


@dataclass
class Symbol:
    """Represents a code symbol (function, class, etc.)."""
    name: str
    type: str  # function, class, method, interface, struct, etc.
    start_line: int
    end_line: int
    doc_comment: Optional[str] = None
    parameters: Optional[str] = None
    return_type: Optional[str] = None
    children: list["Symbol"] = field(default_factory=list)

    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1

    def summary(self) -> str:
        """Short summary for AI agents."""
        parts = [f"{self.type} {self.name}"]
        if self.parameters:
            parts[0] += f"({self.parameters})"
        if self.return_type:
            parts.append(f"→ {self.return_type}")
        if self.doc_comment:
            # Take first sentence
            doc = self.doc_comment.split(".")[0]
            parts.append(f"// {doc}")
        return " ".join(parts)


@dataclass
class FileAnalysis:
    """Complete analysis of a file."""
    file_path: str
    language: str
    total_lines: int
    symbols: list[Symbol]
    imports: list[str]
    dependencies: list[str]  # Other files/modules this depends on
    summary: str = ""

    def compact_output(self, max_symbols: int = 50) -> str:
        """Generate compact output for AI agents."""
        lines = [
            f"File: {self.file_path}",
            f"Language: {self.language}",
            f"Lines: {self.total_lines}",
            f"Symbols: {len(self.symbols)}",
            "",
        ]

        if self.summary:
            lines.append(f"Summary: {self.summary}")
            lines.append("")

        if self.dependencies:
            lines.append(f"Dependencies: {', '.join(self.dependencies)}")
            lines.append("")

        lines.append("--- Structure ---")
        for sym in self.symbols[:max_symbols]:
            indent = "  " * _indent_level(sym)
            lines.append(f"{indent}├── {sym.summary()}")
            for child in sym.children[:10]:
                lines.append(f"{indent}│   ├── {child.summary()}")
            if len(sym.children) > 10:
                lines.append(f"{indent}│   └── ... +{len(sym.children) - 10} more")

        if len(self.symbols) > max_symbols:
            lines.append(f"\n... and {len(self.symbols) - max_symbols} more symbols")

        return "\n".join(lines)


def _indent_level(sym: Symbol) -> int:
    """Determine indentation level based on symbol type."""
    if sym.type in ("class", "struct", "enum", "interface", "protocol", "extension"):
        return 0
    return 1


class BaseAnalyzer(ABC):
    """Base class for language-specific analyzers."""

    def __init__(self, language_name: str, tree_sitter_language):
        self.language_name = language_name
        self.ts_language = ts.Language(tree_sitter_language.language())
        self.parser = ts.Parser(self.ts_language)

    def parse_file(self, file_path: Path) -> Optional[ts.Tree]:
        """Parse a file and return the AST tree."""
        try:
            content = file_path.read_bytes()
            return self.parser.parse(content)
        except Exception:
            return None

    def get_file_content(self, file_path: Path) -> Optional[str]:
        """Get file content as string."""
        try:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

    @abstractmethod
    def analyze(self, file_path: Path) -> Optional[FileAnalysis]:
        """Analyze a file and return structured analysis."""
        pass

    @abstractmethod
    def find_symbols(self, tree: ts.Tree, source: bytes) -> list[Symbol]:
        """Extract symbols from AST tree."""
        pass

    @abstractmethod
    def extract_imports(self, tree: ts.Tree, source: bytes) -> list[str]:
        """Extract imports/dependencies from AST tree."""
        pass

    def get_node_text(self, node: ts.Node, source: bytes) -> str:
        """Get text content of a node."""
        return node.text.decode("utf-8", errors="replace")

    def get_doc_comment(self, node: ts.Node, source: bytes) -> Optional[str]:
        """Extract documentation comment preceding a node."""
        # Look for comment nodes before this node, stopping at any declaration
        declaration_types = (
            "class_declaration", "struct_declaration", "enum_declaration",
            "protocol_declaration", "extension_declaration",
            "function_declaration", "init_declaration", "deinit_declaration",
            "property_declaration", "subscript_declaration",
            "typealias_declaration", "operator_declaration",
            "class_body", "struct_body", "enum_class_body", "enum_body",
        )
        prev_node = node.prev_sibling
        while prev_node:
            if prev_node.type in declaration_types:
                # Stop — another declaration is between us and the comment
                return None
            if prev_node.type in ("comment", "line_comment", "block_comment", "documentation_comment"):
                text = self.get_node_text(prev_node, source)
                # Clean up comment markers
                text = text.lstrip("/").lstrip("*").strip()
                return text
            prev_node = prev_node.prev_sibling
        return None
