# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0076
- Status: Accepted. The owner asked on 2026-10-31 to verify and fix the external review of v0.10.0 and v0.10.1, including a DEC for the CLI sign-in if needed.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Related Requirements: none
- Related Tasks: TASK-0205, TASK-0207, TASK-0208
- Related Architecture: DEC-0071 (CLI workflows, PAT and the browser sign-in), DEC-0009 (layers)

## Context

- `superstep login` uses a device sign-in (DEC-0071): the CLI starts it without credentials, prints a link and a code, and polls until a signed-in person approves on `/cli/authorize`.
- The link carried the code (`/cli/authorize?code=...`) and the page showed it with an Approve button. Anyone could start a sign-in, send the link and wait: one click by a signed-in victim gave the sender a token with the victim's full access (device-code phishing).
- `POST /api/auth/cli/devices` needed no sign-in and had no limit, and expired rows were never removed.
- The CLI sent the saved token to whatever server `--url` or `SUPERSTEP_URL` named.
- RFC 8628 section 5.4 recommends that the user types the code shown on the device, and warns that a `verification_uri_complete` link removes that check.

## Decision

1. **The person types the code.** The link is `/cli/authorize` without the code. The page has an empty code field and a warning to approve only a sign-in they started themselves; a `code` in the link (older CLIs) is ignored. Approve and Deny stay disabled until a code is typed.
2. **Starts are limited.** At most 10 sign-ins per client IP per 10 minutes (the shared rate limiter, Redis when configured); more answer `RATE_LIMITED` with `Retry-After`.
3. **Old sign-ins are removed.** Starting a sign-in deletes rows whose deadline passed more than 10 minutes ago and that hold no undelivered token.
4. **The saved token stays with its server.** The CLI sends the token from `~/.superstep/cli.json` only to the server it was issued by (scheme, host and port compared, default port and trailing slash ignored). Another URL gets no token: log in there, or set `SUPERSTEP_TOKEN` explicitly.
6. **The token is minted when the CLI collects it** (amended 2026-10-31, TASK-0207). Approval records the account and the token name only; the first poll after approval mints the token, so no plaintext token waits in `cli_devices`, and a sign-in that expires approved but uncollected leaves nothing usable. A secret stored by an earlier version is revoked and cleared once its sign-in expires.
7. **A name taken before collection gets a suffix** (amended 2026-10-31, TASK-0208). If a token with the approved name was created between approval and the poll, the minted token is named `name (2)`, `name (3)`... (cut to 80 characters), so the poll that won the compare-and-set always delivers a token and the CLI never has to sign in again for it. Chosen over minting in the same transaction as the compare-and-set: that would roll back to approved but still fail on every later poll with PAT_NAME_TAKEN until the sign-in expires, and it needs a transaction across two repositories; the suffix is one small method in the service and the person can rename or revoke the token in Settings.
5. **`last_used` is written at most every 5 minutes** per token, and the unused `PatService.user_for_token` is removed (the request path is `AuthService._from_pat`).

## Rationale

- Typing the code makes the approving person compare it with their own terminal; a phisher's link no longer carries everything needed.
- A per-IP limit is enough for an endpoint that only creates short-lived rows; the codes are random (32 bytes and 4 bytes behind a signed-in approval).

## Alternatives Considered

- Show the code and ask for a checkbox "it matches": weaker, the person can tick without looking.
- Bind the sign-in to the browser that started it: the CLI has no browser session, so not possible.

## Impacts

- `verification_uri` no longer contains the code; the CLI already prints the code next to the link.
- Older CLIs still work; the person types the code the terminal printed.

## Risks

- A sign-in can deliver a token whose name differs from the one approved (`laptop (2)`); it is listed under Settings, Tokens.
- A person can still be talked into typing a code someone else sent; the warning on the page addresses this, as RFC 8628 recommends.

## Owner Decisions

- 2026-10-31: the owner asked for these fixes ("đánh giá lại coi đúng không, nếu có thì hãy fix").

## Approval

- Accepted with TASK-0205.

## Review Or Revisit Trigger

- A report of a phished CLI sign-in, or support for a second sign-in method (SSO for the CLI).
