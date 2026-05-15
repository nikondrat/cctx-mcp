## ADDED Requirements

### Requirement: Transparent live-disk fallback
The system SHALL fall back to live filesystem search when the index-based search returns no results.

#### Scenario: Empty index falls back to rg
- **WHEN** `code_search` or `find_symbols` returns zero results from the index
- **THEN** the system transparently runs a live-disk search using ripgrep (or native Python if rg unavailable)

#### Scenario: Fallback notification
- **WHEN** a live-disk fallback is triggered
- **THEN** the response includes a `_fallback: "live-disk"` indicator so the caller knows the source

#### Scenario: rg not installed
- **WHEN** ripgrep is not installed on the system
- **THEN** the fallback uses Python's built-in `os.walk` + `re` instead, with a `_fallback_method: "python-re"` indicator

### Requirement: Fallback is for empty results only
The system SHALL NOT use live-disk fallback when index-based search has results, to maintain performance.

#### Scenario: Results exist, no fallback
- **WHEN** the index returns at least one match
- **THEN** the system returns index results without triggering a live-disk fallback
