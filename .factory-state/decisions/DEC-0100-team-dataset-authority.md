# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0100
- Status: Proposed 2026-11-13; awaiting the owner's choice
- Owner: Thái Quí Nguyễn
- Created: 2026-11-13
- Updated: 2026-11-13
- Related Requirements: REQ-0100, REQ-0097
- Related Architecture: ARCH-0003
- Related Tasks: TASK-0335

## Context

`team_members` has no role column; roles (`admin`, `editor`, `viewer`) are global. `DatasetService.editable_definition` only checks global `resources.manage`, so every editor in a team can change schema, delete the team dataset, revoke its grants, and rotate or revoke tokens issued by others. `rotate` also sets the issuer to the rotating user, so the token then acts with that user's authority.

## Options

- Option A (recommended): a team dataset is managed by its owner (creator) and by global admins (`org.manage`). Other team members with `resources.manage` may add, edit, import, and delete rows. Only managers change schema, delete the dataset, grant or revoke workflow access, and issue, rotate, or revoke tokens. Rotation keeps the original issuer. Admins may transfer dataset ownership to another team member.
- Option B: add a `role` (`manager`, `editor`, `viewer`) to `team_members` and use it for datasets. More flexible, but it introduces team roles that workflows and other resources do not honor, and needs team admin UI.
- Option C: keep the current behavior and document it.

## Decision

Proposed: Option A, with ownership transfer by admins.

## Rationale

- Option A needs no new membership model, matches how personal datasets already behave (owner-managed), and closes the destructive paths found in the review.
- Option B is a cross-cutting change to teams and belongs in a separate requirement if team roles are wanted product-wide.

## Impacts

- Studio shows managers' actions disabled with an explanation for other members (TASK-0340 show-and-explain).
- A team dataset whose owner leaves the team stays manageable by admins, who can transfer ownership.
- Existing tokens keep their recorded issuer; tokens already rotated by another member keep the issuer that rotation set (no data rewrite).
