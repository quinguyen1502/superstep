# Review

## Metadata

- Project: superstep
- Review ID: REV-0249
- Task ID: TASK-0267
- Reviewer: Grok (advisory; owner authorised the work and green merge, "Do it" 2026-11-07)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

HTTP helpers in `python_export.py` / `typescript_export.py`, `tests/test_export_http_pinning.py`, handbook en/vi rows, DEC-0088.

## Findings

### Blocking

- None.

### Non-Blocking

- Python connects to `addresses[0]` (resolver order) like `core/net.py`; no fallback to the other checked addresses if the first is unreachable (Studio behaves the same).
- TypeScript now uses `node:http(s)` instead of `fetch`; `timeout` is the socket idle timeout (30 s), not a total deadline as `AbortSignal.timeout` was. Response bodies are buffered in memory as before.
- Tests prove the behaviour discriminates: on the previous develop code the rebind and TLS/SNI tests fail (4 failed), with this change all pass.
- Tests trust a throw-away test CA through `SSL_CERT_FILE` (httpx) / `DENO_CERT` (Deno); production uses the platform trust store unchanged.

## Standards And Architecture Alignment

Matches `core/net.py` (resolve once, all answers checked, connect to the checked IP, Host + SNI on the name). No secrets emitted.

## Review Decision

Approved for QA.
