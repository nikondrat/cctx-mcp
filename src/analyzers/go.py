"""Go language analyzer using tree-sitter."""

from pathlib import Path
from typing import Optional

import tree_sitter as ts
import tree_sitter_go

from analyzers.base import BaseAnalyzer, FileAnalysis, Symbol


class GoAnalyzer(BaseAnalyzer):
    """Analyzer for Go source files."""

    def __init__(self):
        super().__init__("go", tree_sitter_go)

    def analyze(self, file_path: Path) -> Optional[FileAnalysis]:
        """Analyze a Go file."""
        content = self.get_file_content(file_path)
        if content is None:
            return None

        tree = self.parse_file(file_path)
        if tree is None:
            return None

        source = content.encode("utf-8")
        symbols = self.find_symbols(tree.root_node, source)
        imports = self.extract_imports(tree.root_node, source)

        dependencies = [imp.split("/")[-1] for imp in imports if imp]

        symbol_types = {}
        for sym in symbols:
            symbol_types[sym.type] = symbol_types.get(sym.type, 0) + 1

        type_summary = ", ".join(f"{count} {t}" for t, count in symbol_types.items())
        summary = f"Go file with {type_summary}"

        return FileAnalysis(
            file_path=str(file_path),
            language="go",
            total_lines=len(content.splitlines()),
            symbols=symbols,
            imports=imports,
            dependencies=dependencies,
            summary=summary,
        )

    def find_symbols(self, node: ts.Node, source: bytes) -> list[Symbol]:
        """Extract symbols from Go AST."""
        symbols = []
        self._collect_symbols(node, source, symbols)
        return symbols

    def _collect_symbols(self, node: ts.Node, source: bytes, symbols: list[Symbol], parent: Optional[Symbol] = None):
        """Recursively collect symbols from AST."""
        symbol_map = {
            "type_declaration": "type",
            "function_declaration": "function",
            "method_declaration": "method",
            "interface_type": "interface",
            "struct_type": "struct",
        }

        if node.type in symbol_map:
            sym_type = symbol_map[node.type]
            name = self._get_symbol_name(node, source)
            if name:
                doc = self.get_doc_comment(node, source)
                params = self._get_parameters(node, source) if sym_type in ("function", "method") else None
                return_type = self._get_return_type(node, source) if sym_type in ("function", "method") else None

                sym = Symbol(
                    name=name,
                    type=sym_type,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    doc_comment=doc,
                    parameters=params,
                    return_type=return_type,
                )

                if parent is None:
                    symbols.append(sym)
                else:
                    parent.children.append(sym)
                return

        for child in node.children:
            self._collect_symbols(child, source, symbols, parent=parent)

    def _get_symbol_name(self, node: ts.Node, source: bytes) -> str:
        """Extract symbol name from Go declaration."""
        for child in node.children:
            if child.type == "type_identifier" or child.type == "field_identifier" or child.type == "identifier":
                return self.get_node_text(child, source)
            if child.type == "type_spec":
                for spec_child in child.children:
                    if spec_child.type == "type_identifier":
                        return self.get_node_text(spec_child, source)
        return ""

    def _get_parameters(self, node: ts.Node, source: bytes) -> Optional[str]:
        """Extract parameters from function/method declaration."""
        for child in node.children:
            if child.type == "parameter_list":
                params = []
                for param in child.children:
                    if param.type == "parameter_declaration":
                        params.append(self.get_node_text(param, source))
                return ", ".join(params) if params else None
        return None

    def _get_return_type(self, node: ts.Node, source: bytes) -> Optional[str]:
        """Extract return type from function declaration."""
        for child in node.children:
            if child.type in ("type_identifier", "slice_type", "pointer_type"):
                return self.get_node_text(child, source)
        return None

    def extract_imports(self, node: ts.Node, source: bytes) -> list[str]:
        """Extract import statements from Go file."""
        imports = []
        self._collect_imports(node, source, imports)
        return imports

    def _collect_imports(self, node: ts.Node, source: bytes, imports: list[str]):
        """Recursively collect import statements."""
        if node.type == "import_declaration":
            for child in node.children:
                if child.type == "import_spec":
                    for spec_child in child.children:
                        if spec_child.type == "interpreted_string_literal":
                            # Remove quotes
                            text = self.get_node_text(spec_child, source)
                            imports.append(text.strip("\""))
        elif node.type == "import_spec_list":
            for child in node.children:
                if child.type == "import_spec":
                    for spec_child in child.children:
                        if spec_child.type == "interpreted_string_literal":
                            text = self.get_node_text(spec_child, source)
                            imports.append(text.strip("\""))
        for child in node.children:
            self._collect_imports(child, source, imports)
