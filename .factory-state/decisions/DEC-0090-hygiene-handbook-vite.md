# Decision

- Decision ID: DEC-0090
- Project: superstep
- Status: implementation direction within owner-authorised REQ-0091
- Created/Updated: 2026-11-09
- Related: REQ-0091, PLAN-0011, DEC-0085 (browser defaults unchanged)

Browser product defaults are not flipped in this work: STUDIO_ENABLE_BROWSER / STUDIO_ENABLE_BROWSER_RUNTIME remain opt-in; connection allow_evaluate_js / allow_upload / allow_download remain default false; require_mutating_approval remains default false per DEC-0085. The owner receives a report only.

Comment hygiene strips parenthetical and leading factory IDs from comments/docstrings without changing runtime behaviour. Vite ESM configs use `import.meta.dirname` (Node 20.11+ / Vite-supported) instead of `__dirname`. Handbook Vietnamese is a full translation sync of the English browser guide; other pages already matched heading structure and volume.
