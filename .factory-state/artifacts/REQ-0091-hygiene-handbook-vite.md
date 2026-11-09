# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0091
- Status: Owner-authorised 2026-11-09 ("Tiến hành xử lý…" — browser defaults report; remove task IDs from code comments; Vite `__dirname` warning; no Vietnamese in source except translations; sync Vietnamese handbook)
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-09
- Related: PLAN-0011, DEC-0090; browser defaults are a report only (REQ-0086 / DEC-0085 unchanged)

## Summary And Scope

1. Report which browser-tool pieces are not on by default (no silent product-default flips).
2. Remove factory artifact IDs (TASK-/REQ-/DEC-/…) from source comments and docstrings; keep useful English.
3. Replace `__dirname` with `import.meta.dirname` in Vite configs.
4. Vietnamese stays only in translation catalogs / handbook vi / intentional bilingual message maps; not in identifiers or non-i18n source.
5. Sync Vietnamese handbook pages with English (especially browser guide); remove task codes from handbook pages.

## Acceptance Criteria

- Browser defaults report delivered with file/line evidence.
- Source under backend/app, frontend/src, packages/react/src, sdk/*/src, scripts has no TASK-/REQ-/DEC-/PLAN-/ARCH-NNNN in comments/docstrings; Python compiles.
- Vite configs use `import.meta.dirname`.
- Handbook en/vi page set parity; vi/guide/browser.md matches en structure; no task codes in handbook md (except generated OpenAPI if any residual).
- factory deps apply / verify / validate; REV/QA; CI green before merge.
