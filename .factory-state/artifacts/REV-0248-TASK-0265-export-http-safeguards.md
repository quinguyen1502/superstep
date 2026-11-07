# Review

## Metadata

- Project: superstep
- Review ID: REV-0248
- Task ID: TASK-0265
- Reviewer: Grok (advisory; owner authorised the fixes and green merge)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

`export_common.py` (`http` use flag), HTTP helpers and call sites in `python_export.py` / `typescript_export.py`, `tests/test_export_http_safeguards.py`, updated assertions in export tests, handbook en/vi rows.

## Findings

### Blocking

- None.

### Non-Blocking

- No IP pinning: DNS could change between check and connect (Studio pins). Documented in DEC-0087 and the handbook.
- TypeScript address classification is hand-written (IPv4 ranges matching Python's `ipaddress` private/reserved sets, IPv6 loopback/ULA/link-local/multicast/doc/mapped/NAT64); IPv4-mapped IPv6 is blocked outright.
- The idempotency key is per run id + request, not per node iteration as in Studio: identical repeated requests in one run share a key (safe direction).
- Deno now needs `--allow-net` (already required for real models); documented.

## Standards And Architecture Alignment

Security parity is stronger than the previous export (which had none of these checks). No secrets emitted; credentials in URLs remain whatever the user typed in the canvas, now sent as a header.

## Review Decision

Approved for QA.
