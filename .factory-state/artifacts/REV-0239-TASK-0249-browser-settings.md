# Review

## Metadata

- Project: superstep
- Review ID: REV-0239
- Task ID: TASK-0249
- Reviewer: Codex (self-review; owner review pending)
- Created: 2026-11-06
- Updated: 2026-11-06
- Outcome: scoped conditional pass; full declared verification running

## Review Scope And References

Source 14b1560a relative to task-start 34739b8b. REQ-0086, DES-0004,
ARCH-0002/DEC-0085, PLAN-0006, docs/ui-conventions.md and
docs/browser-settings.md. Explicit unmerged stack on TASK-0248 source 27cdf07d
(base 07d22fce); predecessor #313 final 50a536ce records full checks passed.
Parent metadata/locale follow-up is not incorporated in this branch yet.

## Findings

No blocking source finding after scoped checks. Typed browser/web controls extend
existing Settings cards; no new navigation/node/tab or browser model loop.
Provider, proxy, origin policy, encrypted personal seed and bounded session
settings belong to the connection. Normalisation preserves malformed policy for
validation rather than dropping it to an unrestricted list. Inactive credentials
are excluded; stored active secrets submit null for keep, never readback.
Required secret clearing cannot save an unusable active configuration.

Resolved during implementation: canonical origin duplicates, idle/lifetime
relationship and profile/allowed-origin subset now have translated field errors.
Provider/proxy draft values survive toggling without granting inactive authority.
Unsupported SOCKS/CDP/WSS transports fail at labelled fields. Remote discovery
is explicitly metadata only; operator approval remains independent.

Non-blocking: browser capability-unavailable rendering is tested by withholding
adapter metadata in the fixture; live production flag changes are not exercised.
No actual external provider/proxy/account is configured in this UI task.

## Standards And Design Alignment

Shared shadcn controls/theme tokens, api() envelope/error handling, identical
en/vi keys and glossary. Exact-name shared confirmation covers connection,
profile and explicit secret removal, including existing generic secret rows.
Configuration URLs are literal connection fields; no node template field changes.
No schema/dependency/backend changes. Inline cards are retained; no long dialog
is introduced. Node tabs remain General/Settings/Data/Execution for TASK-0250.
Colour/hex checks on changed components return no hits; strict UI lint passes.

## Validation Review

Six helper cases + five locale tests pass. Real Chrome: four en/vi × light/dark
browser/proxy/profile/web cases pass (42.4 s), plus remote/controller/metadata
case and four existing HTTP API + one stdio MCP regression (6 passed, 46.6 s).
Tests cover encrypted edit/keep, discover, field-error focus, exact-name delete,
anonymous API denial, keyboard tab order and 390px no overflow. Wide/narrow and
web screenshots at /private/tmp/superstep-browser-settings-shots-20261106 were
visually inspected; none committed. Lint passes with existing unrelated warnings.
Full eight-command Factory profile running on clean source 14b1560a.

## Assumptions, Follow-Up And Decision

Owner chain instruction authorises implementation/validation/Draft PR, not
merge or production setup. Parent metadata sync awaits explicit permission after
automatic approval review rejected git merge; this does not block UI checks.
Conditionally approved for scoped QA pending full declared verification and owner
review. Runtime remains experimental/default off. No done/Ready/merge approval.
