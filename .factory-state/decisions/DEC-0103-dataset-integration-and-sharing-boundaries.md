# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0103
- Status: Accepted for planning
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-22
- Related Requirements: REQ-0103
- Related Architecture: ARCH-0005

## Context

Dataset rows have a scoped Connected v1 API, Studio read and write routes, and per-row revisions. The accepted next scope adds supported integration clients, live Studio refresh, and a limited anonymous view.

## Decision

1. Publish the existing Connected v1 surface and use its scoped credential in both official SDKs.
2. Use authorized post-commit invalidations and an authoritative re-read for Studio. A separate persisted marker supports recovery.
3. Share a server-enforced read-only view with a distinct revocable capability.

## Rationale And Alternatives

- Adding a new general CRUD API in the first milestone would duplicate permissions and write retry behavior. The Connected contract already serves the six planned operations.
- A replayable feed could serve workflow triggers or external subscribers. The Studio milestone needs fresh displayed state and can recover it with the existing query API.
- Sharing the entire Dataset would simplify configuration but expose more data than the manager needs to publish. Field projection and a fixed filter allow narrower sharing. Public write access and standalone synchronization have different permission and consistency requirements.

## Approval

The owner accepted the scope and sequencing for planning on 2026-11-22. Detailed routes, migrations, limits and UI are implementation proposals to review within each task. Deployment, package publication and PR merges follow their normal owner approval.

## Review Triggers

Revisit when planning durable change triggers, general CRUD or schema discovery for API users, or public Relation, export or realtime capabilities.
