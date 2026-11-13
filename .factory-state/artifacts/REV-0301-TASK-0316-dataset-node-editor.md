# Review

## Metadata

- Project: superstep
- Review ID: REV-0301
- Task ID: TASK-0316
- Reviewer: Codex
- Created: 2026-11-13
- Updated: 2026-11-13
- Outcome: Approved for QA

## Review Scope

Dataset node settings and data mapping, workflow grant status, template portability, editor and trace metadata, locales, and browser coverage. Reviewed against the accepted Dataset requirement, design, architecture, and UI conventions.

## Findings

- Settings reads only the effective permission for a dataset and workflow both visible to the user. Runtime continues to enforce grants independently.
- Configuration saves column keys while displaying current labels. Changed bindings check authoring access even when incomplete, and fully configured bindings validate column references and the unique upsert key.
- Template sanitization clears the installation-specific Dataset ID. The configuration keeps key-based mappings and can remove unavailable fields after rebinding.
- The trace reads the Dataset operation's returned dry-run flag. The Studio and shared React chat UI reuse the same node icon.
- No blocking findings in the scoped diff.

## Standards And Design

Uses existing shadcn inputs, typed state template editors, semantic colors, and translated strings in English and Vietnamese. The Playwright flow checks filter-control alignment. Both themes were visually reviewed. The local linked dependency tree caused the screenshots to use the browser's fallback font.

## References

- [Task](../tasks/done/TASK-0316-dataset-node-editor.md)
- [QA](QA-0301-TASK-0316-dataset-node-editor.md)
