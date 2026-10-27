---
name: task-validation
description: Run the project's declared validation commands (format, analyze, lint, test, build) for the active task and report results. Use when the user asks to validate, test, run checks, or verify a change after a scoped-change or other "stop before validation" step.
---

# Task Validation

Run and report validation for the active task using the project's canonical tool policy. Do not implement, refactor, or fix behavior in this skill; report failures instead.

## Inputs

- Read `.factory-state/tooling/tool-policy.yaml` for declared commands (`format`, `analyze`, `lint`, `test`, `build`, or project-specific names).
- `factory verify` runs the same file. A command is included when its name or `kind` is `check`, `test`, `lint`, `typecheck`, `build`, `format`, or `analyze`. Once any of those entries exist, verify does not discover a second command list.
- If no tool policy exists, ask the user which commands to run before proceeding. Do not invent commands.
- Note which validation profile the user requested when it matters (quick vs full). Default to running all declared commands.

## Execution

- Run each command exactly as declared. Do not add extra flags unless the user asks.
- Run in a clean working tree. If the tree is dirty, ask the user whether uncommitted changes should be included.
- Stream or capture output so failures can be reproduced.
- Stop on the first failure only if the user asked for fail-fast; otherwise run all declared commands and collect all failures.

## Reporting

- Report each command with pass or fail, duration if useful, and the exact failure message on failures.
- On failure, do not attempt to fix. Report the failing command, the offending file and line when the tool provides them, and the smallest next action the user or a follow-up skill should take.
- If the active task requires an activity log entry per project standards, update it with the validation outcome and evidence path. Do not update unrelated artifacts.
- Do not mark the task as QA-passed or reviewed. That belongs to the review or QA skill.

Do not push, tag, or promote a PR based on validation outcome alone.
