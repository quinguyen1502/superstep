# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0239
- Task ID: TASK-0249
- QA Owner: Codex (advisory; owner approval pending)
- Created: 2026-11-06
- Updated: 2026-11-06
- Outcome: scoped conditional pass; full declared verification running

## Scope And References

Source 14b1560a; TASK-0249, REQ-0086, DES-0004, ARCH-0002/DEC-0085,
PLAN-0006, REV-0239, docs/browser-settings.md and docs/ui-conventions.md.

## Acceptance Criteria Coverage

- Configure/discover local/controlled remote without secret readback or re-entry:
  passed real UI/API create/edit/discover and stored-empty save. Synthetic
  controller/proxy secrets absent from responses; browser/runtime calls are not
  launched by metadata discovery.
- Connection-level proxy, stable session policy and separate web configuration:
  passed direct/custom/basic/operator-default controls, inactive authority
  exclusion, separate search/fetch setup and no browser proxy controls on web.
  Session immutability/egress enforcement use previously tested backend contracts;
  this task changes no runtime code.
- Unsupported combinations and access: passed translated SOCKS/WSS/token/search
  field errors with focus/aria links, profile personal-only restriction,
  canonical policy/limit checks, anonymous API 401 and disabled-adapter UI.
  Backend remains authoritative for addresses, seed contents and access.
- Keyboard/narrow/themes/locales and typed deletion: passed four en/vi ×
  light/dark cases, 390px document overflow assertion, keyboard Tab between proxy
  controls, exact-name mismatches/confirmations for secret/profile/connection.

## Checks Performed

- browser-settings.test.ts: 6 passed; locales.test.ts: 5 passed.
- browser-connections.spec.ts matrix: 4 passed (42.4 s).
- Remote/disabled-metadata case + managed-http-api.spec.ts (4) + mcp.spec.ts (1):
  6 passed (46.6 s), real isolated local app/DB and system Chrome.
- npm run lint: passed strict UI class guard, no new component warnings. Existing
  unrelated lint/Vite/dev-key/socket shutdown warnings remain.
- Colour/hex scan on changed components: no hits; git diff --check passed.
- Full Factory eight-command profile running on committed source 14b1560a.

## UX And Accessibility Evidence

Shared controls/tokens/dialog; associated labels, aria-invalid/describedby,
role=alert, first-error focus and required range hints. Wide browser/web and
narrow screenshots for both locales/themes are outside Git at
/private/tmp/superstep-browser-settings-shots-20261106; visual inspection found
no clipped fields, unreadable theme text or horizontal overflow. Existing Settings
cards use page scrolling. No new node/template/tab/dialog layout is added.

## Defects, Gaps And Residual Risk

No unresolved scoped defect. Full canonical verification still pending. UI
discovery does not attest remote enforcement or test a real proxy route; actual
runtime/HTTPS/Docker proofs belong to prerequisites. Metadata-unavailable test is
a controlled UI response, not live operator reconfiguration. Seed validation and
DNS/egress approval remain server-enforced. Screenshot/Agent/recipe/trace UI and
code exports remain TASK-0250/0251/0252. Default runtime stays off.

## QA Decision

Conditionally passed for scoped review pending full profile and owner approval.
No done/Ready/merge authority. Parent follow-up sync is separately awaiting
permission after automatic merge-review rejection; current source is committed
and testable independently.
