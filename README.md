# Code Context

MCP server for efficient code context retrieval - reduces AI agent token usage by providing structured code summaries instead of full file reads.

## Problem

AI agents waste tokens reading entire files when they only need to understand structure. A 500-line file costs ~1500 tokens to read, but only ~200 tokens are needed for the structure.

## Solution

Code Context uses tree-sitter to parse code and return:
- Symbol hierarchy (classes → methods → properties)
- Dependencies/imports
- Documentation comments
- Line counts per symbol

## Installation

```bash
cd /Users/a1/dev/tools/code-context
uv sync
```

## Usage

### As MCP Server

Add to your MCP config:
```json
{
  "mcpServers": {
    "code-context": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/a1/dev/tools/code-context",
        "run",
        "src/server.py"
      ]
    }
  }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `smart_read` | Structured file analysis |
| `find_symbols` | Search symbols across project |
| `get_dependencies` | File dependencies |
| `trace_calls` | Find symbol usages |
| `analyze_project` | Project structure overview |

## Supported Languages

- Swift
- Python
- TypeScript/JavaScript
- Rust
- Go
- Dart

## Architecture

```
src/
├── server.py           # MCP server with tools
├── cache.py            # Disk-based caching
├── search.py           # Project search and analysis
└── analyzers/
    ├── base.py         # Base analyzer interface
    ├── swift.py        # Swift analyzer
    ├── python.py       # Python analyzer
    ├── typescript.py   # TypeScript/JS analyzer
    ├── rust.py         # Rust analyzer
    ├── go.py           # Go analyzer
    └── dart.py         # Dart analyzer
```

## Token Savings

| Approach | Tokens per 500-line file |
|----------|--------------------------|
| Standard read | ~1500 tokens |
| `smart_read` | ~200 tokens |
| **Savings** | **~87%** |

## License

MIT
