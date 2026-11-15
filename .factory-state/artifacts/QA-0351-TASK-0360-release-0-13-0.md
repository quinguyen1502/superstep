# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0351
- Task ID: TASK-0360
- QA Owner: Codex
- Created: 2026-11-15
- Updated: 2026-11-15
- Outcome: pass for draft review

## Acceptance Criteria Coverage

- Compared remote tags with public npm and PyPI metadata. Candidate versions were available at the time of review.
- Clean offline npm workspace installation, frontend production build, and version checks passed.
- Python installer and release tests passed (6). Built the 0.13.0 wheel and source distribution in an isolated environment.
- TypeScript generated types, type checks, unit tests (106), ESM and CommonJS smoke, and package dry run passed.
- React lint, unit tests (22), and package dry run passed.
- Both handbook builds and their image checks passed.
- A temporary SQLite database upgraded from migration 0058 to revision 0071. This check used a separate database from the local Dataset demo.

## Gaps

CI, PostgreSQL upgrade coverage in CI, and registry publication remain release gates. This review reports local candidate verification. Artifact and publication jobs should run against the checked release commit.

## Integrated CI Follow-Up

- GitHub Actions [PostgreSQL run](https://github.com/quinguyen1502/superstep/actions/runs/43687813378/job/132731879376) failed the Usage series assertion while overall counts matched.
- Reproduced the same boundary problem on SQLite with runs immediately before, at, and after a fractional bucket boundary. The old query placed all three runs in the next bucket.
- The corrected query keeps timestamp precision until computing the bucket and groups by the floored index. The summary test now uses a fixed clock to assert the documented half-open intervals.
- Local targeted validation passed: 14 tests across Usage, layer boundaries, and the API envelope. Three PostgreSQL cases await the CI service.
