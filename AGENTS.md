# Code Context - AI Agent Guide

## What is this?

Code Context is an MCP server that provides **efficient code analysis** for AI agents. Instead of reading entire files (which wastes tokens), it returns structured summaries of code structure.

## When to use

| Scenario | Use | Don't use |
|----------|-----|-----------|
| Understanding file structure | ✅ `smart_read` | ❌ Read entire file |
| Finding a function/class | ✅ `find_symbols` | ❌ Grep manually |
| Understanding dependencies | ✅ `get_dependencies` | ❌ Parse imports manually |
| Finding where code is used | ✅ `trace_calls` | ❌ Search line by line |
| File < 50 lines | ❌ Just read it | ✅ Overkill |

## Available Tools

### `smart_read(file_path, project_path?)`
Returns structured analysis of a file:
- Symbol hierarchy (classes → methods)
- Dependencies/imports
- Line counts per symbol
- Documentation comments

**Example:**
```
smart_read(file="AuthProvider.swift", project_path="/Users/a1/dev/events_cloud")
```

### `find_symbols(project_path, name?, symbol_type?)`
Search for symbols across a project:
- By name (case-insensitive)
- By type (function, class, method, interface, struct, enum, protocol)

**Example:**
```
find_symbols(project_path="/Users/a1/dev/events_cloud", name="login", symbol_type="function")
```

### `get_dependencies(file_path, project_path?)`
Get imports/dependencies of a file.

**Example:**
```
get_dependencies(file="NetworkService.swift", project_path="/Users/a1/dev/events_cloud")
```

### `trace_calls(symbol_name, project_path)`
Find where a symbol is used across the project.

**Example:**
```
trace_calls(symbol_name="AuthProvider.login", project_path="/Users/a1/dev/events_cloud")
```

### `analyze_project(project_path, max_depth?)`
Get project structure overview with file counts and languages.

**Example:**
```
analyze_project(project_path="/Users/a1/dev/events_cloud", max_depth=2)
```

## Token Savings

| Approach | Tokens per 500-line file |
|----------|--------------------------|
| Standard read | ~1500 tokens |
| `smart_read` | ~200 tokens |
| **Savings** | **~87%** |

## Supported Languages

- Swift (.swift)
- Python (.py)
- TypeScript/JavaScript (.ts, .tsx, .js, .jsx)
- Rust (.rs)
- Go (.go)
- Dart (.dart)

## Configuration

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
        "server.py"
      ]
    }
  }
}
```

## Best Practices

1. **Always use `smart_read` first** - understand structure before diving deep
2. **Use `find_symbols` for navigation** - don't grep manually
3. **Use `trace_calls` for impact analysis** - understand what breaks when you change something
4. **Only read full files when necessary** - when you need implementation details
5. **Cache is automatic** - analyses are cached for 24 hours
