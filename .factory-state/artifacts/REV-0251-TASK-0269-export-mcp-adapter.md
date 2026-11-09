# Review

## Metadata

- Project: superstep
- Review ID: REV-0251
- Task ID: TASK-0269
- Reviewer: Grok (advisory; owner authorised, "Do it" 2026-11-07)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

`export_common.py` (internal `_mcp_server` grouping key, `mcp_prefix`), MCP adapter blocks and call sites in `python_export.py` / `typescript_export.py`, `tests/test_export_mcp_adapter.py`, updated assertions in export tests, handbook en/vi.

## Findings

### Blocking

- None.

### Non-Blocking

- No private-address guard or IP pinning for `<PREFIX>_URL`: it is operator configuration, not workflow data (Studio guards user-registered servers). Documented in DEC-0088 and the handbook.
- stdio MCP servers are not supported by the export; such a node needs an HTTP endpoint (or a custom replacement).
- Prefix numbering follows first use in the file; editing the workflow can renumber servers. The comment above the adapter lists the prefixes.
- Server-initiated requests (sampling, roots) inside a tools/call are not answered, as in Studio's HTTP transport.
- Browser connections (TASK-0251/0252/0261/0262 paths) are untouched: `note_mcp` returns before the prefix for browser data.

## Standards And Architecture Alignment

Ports `engine/mcp_client.py` semantics; `sanitize` still blanks server ids (asserted: `srv-a` absent).

## Review Decision

Approved for QA.
