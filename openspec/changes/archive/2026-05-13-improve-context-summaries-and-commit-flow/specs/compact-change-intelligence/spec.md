## ADDED Requirements

### Requirement: Compact change summary tool MUST provide structured diff intelligence
The system MUST expose a tool that summarizes staged and unstaged git changes into a compact structured format including affected files, change types, and high-level intent cues.

#### Scenario: Compact summary generated from working tree
- **WHEN** a client requests compact change intelligence for the current repository state
- **THEN** the tool returns structured output containing changed files and categorized change signals suitable for downstream commit drafting

### Requirement: Local commit drafting MUST consume compact summaries
The system MUST provide a local commit-drafting path that uses compact change intelligence output to produce candidate commit messages and brief rationale.

#### Scenario: Candidate commit message generated locally
- **WHEN** compact change intelligence is available for current changes
- **THEN** the local drafting step returns at least one candidate commit message with a short rationale mapped to detected change signals

### Requirement: Cloud commit flow MUST support approve/edit gate
The system MUST keep cloud/user approval as a gate before final commit creation, even when local commit draft candidates are available.

#### Scenario: Draft requires approval before commit
- **WHEN** a local commit draft is produced
- **THEN** final commit creation is blocked until the cloud/user layer explicitly approves or edits the draft message

### Requirement: Prompt rewriter MUST remain out of scope for this change
The system MUST NOT automatically rewrite user prompts in this change; only a documented follow-up item is allowed.

#### Scenario: No automatic rewrite in current change
- **WHEN** this change is implemented
- **THEN** no automatic request rewriting is executed prior to main model invocation
