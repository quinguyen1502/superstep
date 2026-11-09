# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0092
- Status: Owner-authorised 2026-11-09 (pt253u: enable browser feature gate only; keep connection-level defaults; translate remaining Vietnamese in `dev.sh`)
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-09
- Related: DEC-0091, PLAN-0012, DEC-0085 (connection-level defaults unchanged)

## Summary And Scope

1. Turn `STUDIO_ENABLE_BROWSER` on by default (project convention: unset / `1` enabled, `0` disabled). Do **not** enable `STUDIO_ENABLE_BROWSER_RUNTIME` by default.
2. Do **not** change connection-level defaults: required whitelist, `allow_upload` / `allow_download` / `allow_evaluate_js` stay false, `require_mutating_approval` stays false, web `enabled_tools` stays `['fetch']`.
3. Translate Vietnamese comments in `dev.sh` to English; confirm other top-level/scripts `*.sh` have no Vietnamese.
4. Handbook: EN remains source of truth; only update gate wording where docs claimed both gates default off; strip leftover task IDs in handbook md if any remain (do not rewrite every VI page).

## Acceptance Criteria

- `browser_enabled()` is True when the env var is unset; False when set to `0`; runtime gate still requires explicit `STUDIO_ENABLE_BROWSER_RUNTIME=1`.
- Tests that assumed unset = disabled are updated; new coverage for the default.
- `.env.example`, handbook configuration/browser pages, and operator docs describe the new default.
- `dev.sh` comments are English; no Vietnamese diacritics remain in `*.sh`.
- factory deps apply / verify full / validate; REV/QA; CI green including E2E before merge.

## Amendment 2026-11-09 (pt254u)

6. Broader hygiene: strip factory IDs from comments/docstrings/test titles/scripts across the repo (not only backend/app + frontend/src). Replace Vietnamese in source with English except app translation catalogs and handbook `docs/vi`.
7. Browser UX: keep gated capabilities **visible** with inline guidance and handbook links when runtime or connection toggles block use. Do not hide upload/download/evaluate from discovery; annotate when connection toggles are off. Show runtime-off banner when `STUDIO_ENABLE_BROWSER_RUNTIME` is unset. Connection-level defaults remain unchanged.
