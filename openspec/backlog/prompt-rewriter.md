# Follow-up: Interactive Prompt Clarification-Rewriter

**Deferred from:** `improve-context-summaries-and-commit-flow`
**Status:** backlog

## Why deferred

Explicitly kept out of scope from the initial change. The focus was on semantic summaries and commit drafting. Prompt rewriting is a separate concern with distinct design requirements.

## What's needed

An interactive flow where:
1. User sends a request to the agent
2. Agent detects ambiguity, missing context, or potential misinterpretation
3. Agent asks clarifying question(s) before proceeding
4. User confirms or clarifies intent
5. Agent rewrites the request internally and proceeds

## Constraints

- Must NOT rewrite silently — always ask for confirmation first
- Must track original vs rewritten request for audit/debugging
- Should use the same MCP tool infrastructure (not a separate pipeline)
- Fallback: if clarification is uncertain, proceed with original request

## Acceptance

- [ ] Clarification agent detects when a request is ambiguous
- [ ] Clarification agent generates focused clarifying question(s)
- [ ] User response is integrated into rewritten request
- [ ] Only rewritten request is forwarded to main model
- [ ] Original request is logged for comparison
