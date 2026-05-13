## ADDED Requirements

### Requirement: Vector index detects stale files on each search
The system SHALL check for file modifications (by mtime or hash) on each `semantic_search` call and incrementally re-index only changed files since the last index build.

#### Scenario: Re-index on file change
- **WHEN** a source file in the project is modified
- **AND** `semantic_search` is called after the modification
- **THEN** the modified file SHALL be re-extracted and re-embedded
- **AND** the index SHALL be updated before the search results are returned

#### Scenario: No re-index for unchanged files
- **WHEN** no source files have changed since the last index build
- **THEN** `semantic_search` SHALL use the cached index without re-embedding
- **AND** response latency SHALL be < 500ms for subsequent queries

#### Scenario: Index rebuild on model change
- **WHEN** the embedding model provider or model name changes between server restarts
- **THEN** the system SHALL detect the mismatch from persisted IndexMetadata
- **AND** SHALL rebuild the entire index (not incremental)

#### Scenario: Deleted files removed from index
- **WHEN** a previously indexed file is deleted from the project
- **THEN** on the next `semantic_search` call, chunks from the deleted file SHALL be removed from the index
