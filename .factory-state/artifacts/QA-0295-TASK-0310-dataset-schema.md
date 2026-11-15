# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0295
- Task ID: TASK-0310
- QA Owner: Codex
- Created: 2026-11-12
- Updated: 2026-11-12
- Outcome: Pass for task acceptance

## Acceptance Criteria Coverage

- Personal and team datasets can be created and renamed. API tests verify stable field keys, falsey defaults, option expansion, archived-key reservation and schema revision advancement.
- Cross-user and cross-team enumeration and direct access are denied. A viewer on the owning team can read and is denied schema edits.
- Duplicate names and keys, invalid typed defaults and incompatible changes return documented errors. Simultaneous writes using the same revision produce one success and one conflict.
- The API exercises text, number, boolean, date, datetime, email and select definitions, and normalizes timestamps to UTC.
- The migration upgrades an existing schema with users and a team. Deletion tests verify that SQLite and PostgreSQL remove the matching definitions and preserve team data on member account cleanup.

## Checks Performed

- Targeted Dataset schema, layer and API envelope suite on SQLite. Eleven passed and three PostgreSQL cases were skipped before starting the disposable server.
- Dataset schema and PostgreSQL migration suite with PostgreSQL 17 in a disposable container. Eight passed, including the Dataset tests on both databases.
- Factory project validation and Git whitespace check passed. Factory reported a dependency-installation metadata warning.

## Gaps And Residual Risk

- The Dataset grid, row writes, CSV, runtime grants, Agent access and export are later tasks. This task introduces schema API behavior only.
- GitHub required checks and owner approval still gate merge.

## QA Decision

Task acceptance passed locally. Keep the task under review pending CI and owner approval.
