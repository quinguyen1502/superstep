# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0253
- Task ID: TASK-0271
- QA Owner: Grok (advisory)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass

## Acceptance Criteria Coverage

- Configured send (twice, same run id): envelope To+Cc+Bcc, Bcc absent from headers, AUTH PLAIN user/pw, rendered subject/body, identical 32-hex Message-ID — pass (Python smtplib, Deno nodemailer).
- Private host without opt-in refused, nothing delivered — pass.
- STARTTLS default against a server without STARTTLS refused, nothing delivered — pass.
- Unconfigured offline: dry run with `(offline mock)`; live: refused naming `SMTP_HOST, SMTP_FROM` — pass.
- Node without studio credential: dry run even with SMTP configured and `LLM_PROVIDER` set — pass.
- Invalid recipient stops the run — pass.
- Generated TypeScript type-checks with `deno check` (HTTP + e-mail) — pass.

## Checks Performed

- `tests/test_export_email_adapter.py` (12), export/stub/MCP/retriever suites (283 passed), full `factory verify run`, handbook strict build.

## Gaps Or Untested Areas

- TLS SMTP (STARTTLS success, ssl) not exercised against a local TLS server.

## QA Decision

Pass.
