# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0037
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Source: owner question "Does the app have any feature for sending email right now?", the request "research adding an SMTP config like credentials and adding a send email node", and the approval "OK, build it with the proposed design (a dry run when the credential is missing, plain text + HTML only)" (2026-10-19)

## Summary

Workflow authors save an SMTP server as a credential and add a Send email node that sends one e-mail per run step, with a dry run when no credential is chosen.

## Problem Or Opportunity

- The studio already sends system e-mail (run notifications, approval links, password reset) through the admin's `SMTP_HOST`, but a workflow cannot send e-mail itself. Authors used an HTTP Tool node against a mail API instead.

## Scope

### In Scope

- An SMTP credential (provider registry, kind `email`): host, port, security, user name, sender; the password is the encrypted secret; Test connection signs in without sending
- The `email` node: To, Cc, Bcc, Reply-To, subject and body templates, plain text or HTML, optional result field; validation, effectively-once sending, an hourly recipient quota
- The editor panel, the credential form with presets, docs, tests

### Out Of Scope

- Attachments, OAuth2 sign-in (Gmail / Microsoft XOAUTH2), inbound mail, delivery tracking
- Using the studio's own `SMTP_HOST` for workflow e-mail (the owner chose the dry run instead)

## Stakeholders Or Users

- Workflow authors who notify customers or teams at the end of a flow

## Desired Behavior

- See DEC-0040.

## Business Rules

- At most 50 distinct recipients (To + Cc + Bcc) per e-mail; every address must be valid when the node runs. Fixed addresses are checked when the workflow is validated.
- Without a credential the node sends nothing and writes `{sent: false, dry_run: true, ..., preview}`.
- Only an SMTP credential can serve a Send email node; SMTP credentials are not offered to LLM nodes.
- Private and loopback SMTP hosts are refused unless `STUDIO_SMTP_ALLOW_PRIVATE=1`.
- A workflow owner's Send email nodes reach at most `STUDIO_EMAIL_NODE_HOURLY_LIMIT` (default 100) recipients per hour.
- A recovered run never sends the same node execution twice.

## Constraints

- No new dependency (Python `smtplib`; `aiosmtpd` is already a test dependency).
- Layers per DEC-0009: SMTP delivery lives in `core/` so both the engine and `services/mailer.py` use it.

## Acceptance Criteria

- A credential with settings is created, edited (password kept), tested and listed without its password.
- A run with a credential delivers one message with the right From, To, Cc, Reply-To, no Bcc header, a Message-ID from the idempotency key, and an escaped HTML part plus a text part.
- A dry run sends nothing; a recovered run sends nothing again; the quota and the wrong-credential case fail with their codes.
- en and vi strings, error codes documented, pytest and e2e cover the above.
