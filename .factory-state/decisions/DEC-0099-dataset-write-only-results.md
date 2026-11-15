# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0099
- Status: Accepted 2026-11-13 (Asia/Saigon) by the owner (pt287u, "as recommended"): Option A
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Related Requirements: REQ-0100, REQ-0099, REQ-0097
- Related Architecture: ARCH-0003
- Related Tasks: TASK-0332, TASK-0343, TASK-0327, TASK-0328

## Context

REQ-0097 defines `read`, `write`, and `read_write` grants and tokens, and REQ-0097's own example grants a workflow write access to Tickets. On `develop` at `b12fa14f`, `write` allows insert and upsert, and both return the stored row projected to the requested fields. An upsert carrying only the unique key therefore returns the full existing row, so `write` is in effect `read_write` for any row whose key the caller can guess. Dry-run upsert returns the same values without writing. TASK-0327 (open as PR #383) gives Agents insert and upsert through the write grant, and TASK-0328 opens writes to public chat and the API trigger, so the leak would reach a model and anonymous public callers.

## Options

- Option A (recommended): keep `write`. When the caller lacks read, insert, upsert, dry-run, and replay return `{row: {id, revision}, inserted}` with no `values`, and a requested field projection is refused with `DATASET_GRANT_DENIED`. An Agent tool without Find gets the same identifier-only result. No-op writes keep the revision.
- Option B: remove standalone `write`; allow only `read` and `read_write`. A migration must either widen existing `write` grants and tokens to `read_write` (silently grants reads) or revoke them (breaks running workflows and deployed exports).

## Decision

Accepted: Option A. Keep `write`. A caller without read permission receives `{row: {id, revision}, inserted}` from insert, upsert, dry-run, and replay, never cell values; a requested field projection from such a caller is refused with `DATASET_GRANT_DENIED`; an Agent tool without Find gets the same identifier-only result; a no-op write keeps the revision. The `inserted: false` key-existence signal is accepted as a documented residual risk.

## Rationale

- Option A keeps every existing grant and token valid and keeps the least-privilege use case REQ-0097 was written for (a public ticket form that can file but not read tickets).
- Option B either widens access without consent or breaks deployments, and still leaves the Agent tool case (a tool configured without Find) to be solved the same way as Option A.
- The fix sits in one service function shared by the node, Agent tool, public entry, and connected token paths, so it applies to TASK-0327 and TASK-0328 without editing their task scope.

## Accepted Residual Risk

- Upsert still reports `inserted: false` when the key exists. A write-only caller can therefore learn whether a key value exists. This is inherent to upsert; owners who must hide existence should grant insert-only flows (Insert row) instead. The handbook states this.

## Impacts

- Studio Access dialog explains that Write returns identifiers only. The Dataset node output picker hides fields when the grant is write-only.
- Exported projects: connected bindings receive the server shape; standalone runtimes apply the same rule to Agent tools without Find (TASK-0343).
- Documented response shape change for write-only tokens in `docs/dataset-export.md` and `docs/api-errors.md`.
