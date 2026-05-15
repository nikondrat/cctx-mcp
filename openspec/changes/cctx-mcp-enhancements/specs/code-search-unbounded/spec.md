## ADDED Requirements

### Requirement: Paginated code search
The `code_search` tool SHALL support cursor-based pagination for large result sets.

#### Scenario: Request unlimited results
- **WHEN** `max_results` is set to `0`
- **THEN** the system returns the first page of matches (default page size: 100) with a `next_cursor` field in the response

#### Scenario: Paginate with cursor
- **WHEN** the user provides a `cursor` parameter from a previous response
- **THEN** the system returns the next page of results starting after the cursor, with a new `next_cursor` (or empty if no more results)

#### Scenario: Default max_results behavior
- **WHEN** `max_results` is not set or is a positive integer
- **THEN** the system returns at most that many matches, with no cursor (backward compatible)

### Requirement: Cursor response format
The paginated response SHALL include structured metadata alongside results.

#### Scenario: Paginated response structure
- **WHEN** a paginated `code_search` returns results
- **THEN** the response JSON includes `{"matches": [...], "next_cursor": "<opaque_string>", "total_estimate": <int>}`

#### Scenario: End of results
- **WHEN** there are no more results to return
- **THEN** the `next_cursor` field is empty string `""`
