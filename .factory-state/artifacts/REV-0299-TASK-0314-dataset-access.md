# Review

## Metadata

- Project: superstep
- Review ID: REV-0299
- Task ID: TASK-0314
- Reviewer: Codex
- Created: 2026-11-12
- Updated: 2026-11-12
- Outcome: Approved for QA

## Findings

- Grant creation requires Dataset management, workflow sharing permission and compatible scopes. Workflow authorization requires the effective saved workflow, a matching grant and a permitted operation. Public and unsaved callers are denied.
- Credentials are scoped to one dataset and operation level. Tokens are hashed, issue and rotate responses are non-cacheable, and subsequent authorization checks the current issuer access. Audit stores identifiers and permissions.
- Runtime entry points and the connected API use this policy in their respective follow-up tasks. The current Studio API does not accept scoped tokens as user sessions.

## References

- [Task](../tasks/done/TASK-0314-dataset-access.md)
- [QA](QA-0299-TASK-0314-dataset-access.md)
