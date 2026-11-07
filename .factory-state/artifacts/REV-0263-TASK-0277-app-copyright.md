# Review

## Metadata

- Project: superstep
- Review ID: REV-0263
- Task ID: TASK-0277
- Reviewer: Grok (advisory; not owner approval)
- Created: 2026-11-08
- Updated: 2026-11-08
- Outcome: approved for QA

## Review Scope

`factory/task-0277-app-copyright` against `origin/develop` at `90ab1070`. The diff is `AppMeta`, the English and Vietnamese strings, the footer on the listed Studio pages, the roadmap note, and TASK-0277. No API, schema, or `LICENSE` change.

## Reference Artifacts

- TASK-0277
- `LICENSE`
- `handbook/mkdocs.base.yml` copyright line
- `docs/ui-conventions.md` (DEC-0008)
- `backend/app/api/routes/meta.py` `GET /api/health`

## Findings

### Blocking

- None. No blocking findings.

### Non-Blocking

- A failed `/api/health` read is cached for the life of the page, so a transient failure hides the version until a reload. The copyright still shows.
- The workflow list still fetches `/api/health` on its own for `import_enabled`.
- `oxlint` warns that `new Date()` in `app-meta.tsx` is impure during render. The lint command still exits 0. The same rule already warns on other files.
- A workflow notice (`fixed bottom-4 right-4`) can sit over the footer while that notice is visible.
- The footer spells the person as the handbook does (`Qui Nguyen`). `LICENSE` still says `Thái Quí Nguyễn`, which the owner left unchanged.

## Standards And Architecture Alignment

- UI strings are in `en.json` and `vi.json` and are not identical. Colours are theme tokens (`text-muted-foreground`). The footer is document flow, not a fixed overlay on the editor.
- The version is the health payload from `backend_version()`. No frontend package version is hardcoded.

## Design Alignment

- Signed-in and signed-out pages in scope show one line. The editor canvas and `/c/:slug` do not.
- The line matches the handbook order: Superstep, Qui Nguyen, then the year. Vietnamese prefixes `Bản quyền`.

## Validation Review

- Tool-policy frontend and SDK commands passed on this worktree with arm64 Node. Backend pytest evidence is in QA-0263. `factory verify` was not run through the x86_64 virtualenv.

## Assumptions

- The owner asked to finish this PR, including review, QA, and Ready. That is not a merge approval.

## Required Follow-Up

- CI on the finished head. Do not merge until the owner asks.

## Review Decision

approved for QA
