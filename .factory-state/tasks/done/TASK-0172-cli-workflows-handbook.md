# Task

## Metadata

- Project: superstep
- Task ID: TASK-0172
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0071

## Objective

The handbook tells an operator how to sign in, keep workflows in Git, fail CI on a broken test, and register `superstep mcp` with a local MCP client. The changelog names the commands.

## Scope

### In Scope

- `handbook/docs/en/operate/cli.md` and `handbook/docs/vi/operate/cli.md`: login, the Settings token, `SUPERSTEP_URL` and `SUPERSTEP_TOKEN`, pull and push, the conflict and `--force`, `run`, `test --all` with the JUnit path, and a Claude Desktop snippet for `superstep mcp`.
- The same facts in both languages. Do not translate the command names, flags, env vars or file names.
- `CHANGELOG.md` Unreleased: the phase 2 commands, in English.
- A CI recipe in the CLI page: install the CLI, export the two variables, run `superstep test --all --mock --junit superstep-junit.xml`.

### Out Of Scope

- New screens, new commands or new server behaviour.
- Publishing the package or cutting a tag. The next `v*` tag ships whatever is on `develop`.
- Rewriting the phase 1 install, upgrade or backup sections beyond a link to the new section.

## Inputs

- The commands as merged from TASK-0167 through TASK-0171.
- DEC-0071 decisions 1, 4, 5, 6 and 7.
- The current `handbook/docs/{en,vi}/operate/cli.md` from TASK-0156.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0071-cli-workflows.md`
- Decisions: `DEC-0068-superstep-cli.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- Both handbook pages describe the same commands and the same CI recipe.
- CHANGELOG Unreleased has one bullet for phase 2.

## Implementation Notes

- Read the `--help` text on the merged CLI before writing a flag that the code does not have.
- The MCP snippet is a stdio command: `superstep`, argument `mcp`, and the workflow name. It tells the reader to run `superstep login` first, or to set the two environment variables. It does not embed a token.
- State that `push` refuses a studio change since the last pull, and that `--force` overwrites it. State that `logout` does not revoke the token.

## Constraints

- Docs only. No product code, no migration, no locale JSON.
- Vietnamese page uses the same headings' meaning as the English page. Command lines are identical.

## Dependencies

- Documented the commands merged in PR #214 through PR #218. Review REV-0148. QA QA-0148. Not merged.

## Acceptance Criteria

- The English and Vietnamese CLI pages both include login, pull, push, `--force`, run, test, JUnit, `--mock`, the two environment variables, and the MCP snippet.
- Neither page contains a sample token or a sample password.
- CHANGELOG Unreleased links the behaviour to REQ-0079 and names `login`, `pull`, `push`, `run`, `test` and `mcp`.
- The handbook build still succeeds for en and vi, the same way TASK-0156 checked it.

## Validation Plan

- The handbook build command already used in CI (`.github/workflows/handbook.yml`). Read that file and run the same build.
- Diff the two language pages and confirm the command blocks match.

## Assumptions

- The designer step is skipped. This task extends the existing Operate → CLI page. It does not add a new handbook section.
- A reader of the Vietnamese page can copy a command from it without translating flags.

## Open Questions

- None.

## Activity Log

- 2026-10-30: planned from REQ-0079 phase 2 (DEC-0071). Not started.
- 2026-10-30: owner asked to finish the phase 2 chain in one pass. Handbook pages and CHANGELOG updated from the merged commands. Review REV-0148. QA QA-0148. Task moved to done. Not merged.

## Handoff Notes

- If a later review changed a flag name, the page follows the merged `--help`, not this task's examples.
