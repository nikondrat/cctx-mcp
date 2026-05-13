"""Python language analyzer using tree-sitter."""

from pathlib import Path
from typing import Optional

import tree_sitter as ts
import tree_sitter_python

from code_context.analyzers.base import BaseAnalyzer, FileAnalysis, Symbol


class PythonAnalyzer(BaseAnalyzer):
    """Analyzer for Python source files."""

    def __init__(self):
        super().__init__("python", tree_sitter_python)

    def analyze(self, file_path: Path) -> Optional[FileAnalysis]:
        """Analyze a Python file."""
        content = self.get_file_content(file_path)
        if content is None:
            return None

        tree = self.parse_file(file_path)
        if tree is None:
            return None

        source = content.encode("utf-8")
        symbols = self.find_symbols(tree.root_node, source)
        imports = self.extract_imports(tree.root_node, source)

        dependencies = [imp.split(".")[-1] for imp in imports if imp]

        symbol_types = {}
        for sym in symbols:
            symbol_types[sym.type] = symbol_types.get(sym.type, 0) + 1

        type_summary = ", ".join(f"{count} {t}" for t, count in symbol_types.items())
        summary = f"Python file with {type_summary}"

        return FileAnalysis(
            file_path=str(file_path),
            language="python",
            total_lines=len(content.splitlines()),
            symbols=symbols,
            imports=imports,
            dependencies=dependencies,
            summary=summary,
        )

    def find_symbols(self, node: ts.Node, source: bytes) -> list[Symbol]:
        """Extract symbols from Python AST."""
        symbols = []
        self._collect_symbols(node, source, symbols)
        return symbols

    def _collect_symbols(self, node: ts.Node, source: bytes, symbols: list[Symbol], parent: Optional[Symbol] = None):
        """Recursively collect symbols from AST."""
        symbol_map = {
            "class_definition": "class",
            "function_definition": "function",
            "decorated_definition": "decorator",
        }

        if node.type in symbol_map:
            sym_type = symbol_map[node.type]
            name = self._get_symbol_name(node, source)
            if name:
                doc = self._get_docstring(node, source)
                params = self._get_parameters(node, source) if sym_type == "function" else None

                sym = Symbol(
                    name=name,
                    type=sym_type,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    doc_comment=doc,
                    parameters=params,
                )

                if parent is None:
                    symbols.append(sym)
                else:
                    parent.children.append(sym)

                if sym_type == "class":
                    for child in node.children:
                        if child.type == "block":
                            for block_child in child.children:
                                self._collect_symbols(block_child, source, symbols, parent=sym)
                return

        for child in node.children:
            self._collect_symbols(child, source, symbols, parent=parent)

    def _get_symbol_name(self, node: ts.Node, source: bytes) -> str:
        """Extract symbol name from Python declaration."""
        for child in node.children:
            if child.type == "identifier":
                return self.get_node_text(child, source)
        return ""

    def _get_parameters(self, node: ts.Node, source: bytes) -> Optional[str]:
        """Extract parameters from function definition."""
        for child in node.children:
            if child.type == "parameters":
                params = []
                for param in child.children:
                    if param.type == "identifier":
                        params.append(self.get_node_text(param, source))
                    elif param.type == "default_parameter":
                        params.append(self.get_node_text(param, source))
                    elif param.type == "typed_parameter":
                        params.append(self.get_node_text(param, source))
                return ", ".join(params) if params else None
        return None

    def _get_docstring(self, node: ts.Node, source: bytes) -> Optional[str]:
        """Extract docstring from function or class."""
        for child in node.children:
            if child.type == "block":
                for block_child in child.children:
                    if block_child.type == "expression_statement":
                        for expr in block_child.children:
                            if expr.type == "string" or expr.type == "concatenated_string":
                                text = self.get_node_text(expr, source)
                                # Remove quotes
                                text = text.strip("\"'")
                                if text:
                                    return text.split("\n")[0]  # First line only
        return None

    def extract_imports(self, node: ts.Node, source: bytes) -> list[str]:
        """Extract import statements from Python file."""
        imports = []
        self._collect_imports(node, source, imports)
        return imports

    def _collect_imports(self, node: ts.Node, source: bytes, imports: list[str]):
        """Recursively collect import statements."""
        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    imports.append(self.get_node_text(child, source))
        elif node.type == "import_from_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    imports.append(self.get_node_text(child, source))
                    break
        for child in node.children:
            self._collect_imports(child, source, imports)
