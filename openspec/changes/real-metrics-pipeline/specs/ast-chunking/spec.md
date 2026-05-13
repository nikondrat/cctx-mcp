## ADDED Requirements

### Requirement: _extract_chunks uses tree-sitter analyzers
The `_extract_chunks` function in `vector_index.py` SHALL use language-specific tree-sitter analyzers from `src/analyzers/` instead of regex-based symbol extraction.

#### Scenario: Python file uses PythonAnalyzer
- **WHEN** `_extract_chunks` processes a `.py` file
- **THEN** it SHALL use `PythonAnalyzer.parse_file()` and `PythonAnalyzer.find_symbols()` to extract symbols with accurate line ranges
- **AND** SHALL produce one `Chunk` per symbol with correct nesting (methods inside classes)

#### Scenario: TypeScript file uses TypeScriptAnalyzer
- **WHEN** `_extract_chunks` processes a `.ts` or `.tsx` file
- **THEN** it SHALL use `TypeScriptAnalyzer`

#### Scenario: Unsupported language falls back to regex
- **WHEN** `_extract_chunks` processes a file without a matching analyzer
- **THEN** it SHALL fall back to the current regex-based approach

### Requirement: Markdown chunking remains regex-based
Markdown files (.md, .mdx, .markdown) SHALL continue to use heading-based regex chunking (unchanged).

#### Scenario: markdown unchanged
- **WHEN** `_extract_chunks` processes a `.md` file
- **THEN** it SHALL use `_chunk_markdown()` as before
- **AND** SHALL NOT attempt tree-sitter analysis

### Requirement: Analyzer-based chunks include doc comments
Chunks produced from tree-sitter analyzers SHALL include any doc comment preceding the symbol as part of the snippet.

#### Scenario: doc comment included in snippet
- **WHEN** a Python function has a docstring
- **THEN** the chunk snippet SHALL include the docstring
- **AND** the `symbol` field SHALL match the analyzer's symbol name
