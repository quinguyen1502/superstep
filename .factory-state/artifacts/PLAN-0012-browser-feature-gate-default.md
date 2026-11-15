# Plan

- Plan ID: PLAN-0012
- Project: superstep
- Status: active
- Created/Updated: 2026-11-09
- Related: REQ-0092, DEC-0091, TASK-0280

## Steps

1. Change `browser_enabled()` default; leave `browser_runtime_enabled()` opt-in.
2. Adjust tests and docs (`.env.example`, handbook, `docs/browser-*.md`).
3. Translate `dev.sh` comments; scan `*.sh`.
4. factory verify full + validate; open PR; merge when required checks including E2E are green.
