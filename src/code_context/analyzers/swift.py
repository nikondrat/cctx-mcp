"""Swift language analyzer using tree-sitter."""

from pathlib import Path
from typing import Optional

import tree_sitter as ts
import tree_sitter_swift

from code_context.analyzers.base import BaseAnalyzer, FileAnalysis, Symbol


class SwiftAnalyzer(BaseAnalyzer):
    """Analyzer for Swift source files."""

    def __init__(self):
        super().__init__("swift", tree_sitter_swift)

    def analyze(self, file_path: Path) -> Optional[FileAnalysis]:
        """Analyze a Swift file."""
        content = self.get_file_content(file_path)
        if content is None:
            return None

        tree = self.parse_file(file_path)
        if tree is None:
            return None

        source = content.encode("utf-8")
        symbols = self.find_symbols(tree.root_node, source)
        imports = self.extract_imports(tree.root_node, source)

        # Extract dependencies from imports
        dependencies = [imp.split(".")[-1] for imp in imports if imp]

        # Generate summary
        symbol_types = {}
        for sym in symbols:
            symbol_types[sym.type] = symbol_types.get(sym.type, 0) + 1

        type_summary = ", ".join(f"{count} {t}" for t, count in symbol_types.items())
        summary = f"Swift file with {type_summary}"

        return FileAnalysis(
            file_path=str(file_path),
            language="swift",
            total_lines=len(content.splitlines()),
            symbols=symbols,
            imports=imports,
            dependencies=dependencies,
            summary=summary,
        )

    def find_symbols(self, node: ts.Node, source: bytes) -> list[Symbol]:
        """Extract symbols from Swift AST."""
        symbols = []
        self._collect_symbols(node, source, symbols)
        return symbols

    def _collect_symbols(self, node: ts.Node, source: bytes, symbols: list[Symbol], parent: Optional[Symbol] = None):
        """Recursively collect symbols from AST."""
        symbol_map = {
            "class_declaration": "class",
            "struct_declaration": "struct",
            "enum_declaration": "enum",
            "protocol_declaration": "protocol",
            "extension_declaration": "extension",
            "function_declaration": "function",
            "init_declaration": "method",
            "deinit_declaration": "method",
            "subscript_declaration": "method",
            "property_declaration": "property",
            "typealias_declaration": "typealias",
            "operator_declaration": "operator",
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

                # Collect children (methods inside class, etc.)
                if sym_type in ("class", "struct", "enum", "protocol", "extension"):
                    for child in node.children:
                        self._collect_symbols(child, source, symbols, parent=sym)
                return

        # Continue recursion
        for child in node.children:
            self._collect_symbols(child, source, symbols, parent=parent)

    def _get_symbol_name(self, node: ts.Node, source: bytes) -> str:
        """Extract symbol name from declaration node."""
        # For init/deinit, return the keyword
        if node.type in ("init_declaration", "deinit_declaration"):
            for child in node.children:
                if child.type in ("init", "deinit"):
                    return self.get_node_text(child, source)
            return "init"

        # For functions and methods, name is in simple_identifier (right after 'func')
        if node.type == "function_declaration":
            for child in node.children:
                if child.type == "simple_identifier":
                    return self.get_node_text(child, source)
            return ""

        # For properties, name is in pattern → simple_identifier
        if node.type == "property_declaration":
            for child in node.children:
                if child.type == "pattern":
                    for pchild in child.children:
                        if pchild.type == "simple_identifier":
                            return self.get_node_text(pchild, source)
            return ""

        # For class/struct/enum/protocol/extension/typealias/operator: type_identifier or identifier
        for child in node.children:
            if child.type in ("type_identifier", "identifier", "simple_identifier"):
                return self.get_node_text(child, source)
            if child.type == "user_type":
                return self.get_node_text(child, source)
        return ""

    def _get_parameters(self, node: ts.Node, source: bytes) -> Optional[str]:
        """Extract parameters from function declaration."""
        for child in node.children:
            if child.type == "function_type" or child.type == "value_parameter_clause":
                params = []
                for param in child.children:
                    if param.type == "value_parameter":
                        param_text = self.get_node_text(param, source)
                        # Clean up parameter text
                        param_text = param_text.strip()
                        if param_text:
                            params.append(param_text)
                return ", ".join(params) if params else None
        return None

    def _get_return_type(self, node: ts.Node, source: bytes) -> Optional[str]:
        """Extract return type from function declaration."""
        for child in node.children:
            if child.type == "function_type_result":
                for result_child in child.children:
                    if result_child.type in ("user_type", "tuple_type", "optional_type"):
                        return self.get_node_text(result_child, source)
        return None

    def extract_imports(self, node: ts.Node, source: bytes) -> list[str]:
        """Extract import statements from Swift file."""
        imports = []
        self._collect_imports(node, source, imports)
        return imports

    def _collect_imports(self, node: ts.Node, source: bytes, imports: list[str]):
        """Recursively collect import statements."""
        if node.type == "import_declaration":
            for child in node.children:
                if child.type == "identifier" or child.type == "user_type":
                    imports.append(self.get_node_text(child, source))
        for child in node.children:
            self._collect_imports(child, source, imports)
