# Decision Record

## Metadata

- Project: langgraph-studio
- Decision ID: DEC-0007
- Status: Accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-10-16
- Updated: 2026-10-16
- Related Requirements: REQ-0001, REQ-0002, REQ-0009
- Related Architecture: ARCH-0001
- Related Tasks: TASK-0001 … TASK-0015

## Context

The owner wants to prove feasibility first (login, workflow list, simple core) and defer the repo-import feature and its sandbox to the end. Task IDs were allocated in the old P0/P1/P2 order (DEC-0004).

## Decision

Re-plan into four phases and renumber tasks to follow the new order:

- Phase 1 Feasibility: TASK-0001 context, TASK-0002 CI + deps/verify, TASK-0003 auth/list hardening (new), TASK-0004 core hardening (old TASK-0014), TASK-0005 real LLM providers (old TASK-0003)
- Phase 2 Usable: TASK-0006 HITL, TASK-0007 API/webhook, TASK-0008 versioning, TASK-0009 Postgres/Redis/Compose, TASK-0010 observability
- Phase 3 Advanced: TASK-0011 subgraph/parallel, TASK-0012 RAG, TASK-0013 MCP, TASK-0014 RBAC
- Phase 4 Last: TASK-0015 repo import hardening + container sandbox (old TASK-0004); the existing import feature becomes experimental behind `STUDIO_ENABLE_IMPORT` (default off) — implemented in TASK-0015, not now

Mapping: see Renumbering Map below (moved here from the former `docs/factory-task-renumbering.md`). Supersedes the priority bands of DEC-0004.

## Rationale

Renumbering keeps IDs aligned with delivery order for a small, solo project, at the cost of a one-time mapping.

## Alternatives Considered

- Option: Keep IDs, only reorder roadmap
  - Benefits: follows the framework rule "never renumber after merging"
  - Tradeoffs: IDs no longer reflect order
  - Reason Not Chosen: owner explicitly requested renumbering

## Impacts

- Task IDs that were already on `main` are reused with new meaning; history (commit messages, old branch names `factory/task-0003-…`, `factory/task-0014-…`) keeps old IDs
- Open PRs #1–#3 updated to new IDs; their branch names are unchanged

## Risks

- Deviation from Factory convention (`.factory/docs/artifact-model.md`: "Never renumber after merging"); mitigated by the mapping table and by doing it before any task reached `done`
- `factory ids check --all-refs` can report old filenames on stale refs until PRs merge

## Approval

- Approved By: Thái Quí Nguyễn (owner)
- Approved On: 2026-10-16
- Scope And Limits: one-time renumbering; future collisions follow the framework rule

## Review Or Revisit Trigger

- Any future re-plan: reorder the roadmap instead of renumbering.

## Renumbering Map (2026-10-16)

Owner re-plan (DEC-0007): tasks renumbered to follow phase order. Commit messages and branch names created before this date keep the **old** IDs.

| New ID | Old ID | Title | Phase | Existing branch / PR |
| --- | --- | --- | --- | --- |
| TASK-0001 | TASK-0001 | Confirm project context and technical baseline | 1 Feasibility | — |
| TASK-0002 | TASK-0002 | GitHub Actions CI + Factory deps/verify unblock | 1 Feasibility | `factory/task-0002-add-github-actions-ci-for-backend-tests-and-frontend-build` (#1) |
| TASK-0003 | — (new) | Harden auth/login and workflow list | 1 Feasibility | — |
| TASK-0004 | TASK-0014 | Review and harden core MVP compiler, runtime and run API | 1 Feasibility | `factory/task-0014-plan-mvp-hardening` (#3) |
| TASK-0005 | TASK-0003 | Real LLM providers with per-workflow credentials | 1 Feasibility | `factory/task-0003-configure-real-llm-providers-with-per-workflow-credentials` (#2) |
| TASK-0006 | TASK-0005 | Human-in-the-loop interrupt and resume | 2 Usable | — |
| TASK-0007 | TASK-0007 | Trigger workflows via REST API and webhooks | 2 Usable | — |
| TASK-0008 | TASK-0006 | Workflow versioning with diff and rollback | 2 Usable | — |
| TASK-0009 | TASK-0008 | Postgres + Redis + Docker Compose | 2 Usable | — |
| TASK-0010 | TASK-0009 | Tracing and observability for runs | 2 Usable | — |
| TASK-0011 | TASK-0010 | Subgraphs and parallel branches | 3 Advanced | — |
| TASK-0012 | TASK-0011 | RAG retriever node | 3 Advanced | — |
| TASK-0013 | TASK-0012 | MCP tools as Tool node source | 3 Advanced | — |
| TASK-0014 | TASK-0013 | RBAC and workflow sharing | 3 Advanced | — |
| TASK-0015 | TASK-0004 | Repo import hardening + container sandbox (import experimental, `STUDIO_ENABLE_IMPORT`) | 4 Last | — |

Artifacts renamed with tasks: `REV-0002-task-0003.md` → `REV-0002-task-0005.md`, `QA-0002-task-0003.md` → `QA-0002-task-0005.md` (on the #2 branch).

Requirements and decisions keep their IDs (REQ-0001…0012, DEC-0001…0007).
