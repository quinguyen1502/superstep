# Review

## Metadata

- Project: superstep
- Review ID: REV-0253
- Task ID: TASK-0271
- Reviewer: Grok (advisory; owner authorised, "Do it" 2026-11-07)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

`export_common.py` (`_email_sends`), Send email adapter and node emission in both exporters, TypeScript `NET` block (shared `blockedAddress`), Python std/email imports, `tests/test_export_email_adapter.py`, handbook en/vi, DEC-0088.

## Findings

### Blocking

- None.

### Non-Blocking

- SMTP has no idempotency: a retried run step can deliver twice; the stable Message-ID only lets receivers deduplicate.
- STARTTLS / ssl paths are implemented as in `core/smtp.py` but the tests exercise `SMTP_SECURITY=none` and the STARTTLS-missing refusal only (no local TLS SMTP server).
- Not ported: HTML body format, Reply-To, the studio's per-user e-mail quota, `tls_optional`.
- The TypeScript file needs `npm:nodemailer@^6` at send time (downloaded by Deno on first use).
- Like Studio, the first resolved address is used; a host resolving to IPv6 first needs that address reachable.

## Standards And Architecture Alignment

Same SSRF guard and pinning as Studio SMTP; the credential id is not exported (asserted); settings only from the environment.

## Review Decision

Approved for QA.
