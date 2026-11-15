# Conventions

These conventions apply to the factory framework and may be copied or adapted by project repositories.

## Framework Repository

- Keep only reusable assets in this repository.
- Do not add project implementations, sample applications, or domain-specific examples.
- Do not assume a language, framework, architecture, database, hosting platform, or business domain.
- Keep templates generic and artifact-driven.

## Project Repositories

- Store project-specific context in the project repository, not in the factory repository.
- Use `.factory/` to consume reusable factory assets: agents, workflows, templates, and docs.
- Use `.factory-state/` for project-owned generated workflow state.
- Keep project standards, decisions, tasks, and artifacts under `.factory-state/`.
- Keep source and tests in project-defined locations.
- Document any project-specific deviations from factory guidance.

## Artifact Naming

Default names may be adapted by each project:

- Requirements: `REQ-0001-title.md`
- Discovery: `DISC-0001-title.md`
- Plans: `PLAN-0001-title.md`
- Design: `DES-0001-title.md`
- Architecture: `ARCH-0001-title.md`
- Tasks: `TASK-0001-title.md`
- Reviews: `REV-0001-task-id.md`
- QA: `QA-0001-task-id.md`
- Decisions: `DEC-0001-title.md`
- Completion summaries: `SUM-0001-title.md`

## Code Comments

Language-neutral, and enforced at review rather than by tooling: none of the
failures below is caught by a formatter, a linter, or a test suite. They are
only visible to a reader.

A comment earns its place by changing what a maintainer does. Everything else
is noise that ages badly.

### Write

- **Describe the code, not the session.** The most common failure in
  agent-written code is a comment recording what was found and decided while
  working — an incident, a date, a task id. That is a diary entry. Keep the
  constraint the incident taught; drop the event. "This API identifies a file
  by its path" is the rule. "Found on a device after 2.66 GB had been fetched"
  is how the rule was learned, and belongs in the task's activity log.
- **State a cross-cutting reason once**, on the type or function that owns the
  decision. Copies drift into slightly different claims, and a reader who
  finds one has no way to know it is not the authoritative version.
- **Do not assert the current state of the project.** "Not implemented yet",
  "never compiled", "the list is empty" — these go stale silently, and a
  confidently wrong comment is worse than none. Prefer what the code
  guarantees.
- **Do not stamp provenance.** A task id means nothing to someone reading the
  code, and the history is already in version control and in the workflow
  state. When a reader must know a standing decision, state the rule itself
  in the comment; do not cite the decision or task artifact by ID or path.
  `factory validate` rejects artifact IDs and `.factory-state/` paths in
  product files (see Repository Hygiene).
- **Date a figure only when it must be re-measured.** A measurement a
  standard forbids estimating is worth its date. Nothing else is.
- **Comments in tests are exempt from the incident rule** where the incident
  is why the test must not be simplified — a fixture that would stop
  exercising a rule, or a known boundary recorded as an open question.

### Review

The four checks a reviewer runs against each comment in a diff:

1. Is it describing the code, or the session?
2. Is the same reason stated more than once across files?
3. Does it assert a project state that will go stale?
4. Would a maintainer break something without it? If not, it restates.

**A change that deletes comments in bulk is audited mechanically, never from
the author's list of what mattered.** That list is written by the same memory
that did the cutting and will omit exactly what was forgotten. Extract every
figure and identifier from the deleted lines, subtract what the added lines
contain, and check the remainder against the tree.

## Repository Hygiene

Enforced by `factory validate` (errors, not warnings). Run only these
checks with `factory validate --only hygiene`.

### Artifact isolation

The factory store stays in the project repository so agents and CI can read
it, but product files do not point at it. Product files are every scanned
file except the factory store and the factory-managed instruction surfaces
listed below: source, tests, scripts, examples, SDKs, packages, CI workflows,
README, changelog, and product docs. They must not contain:

- artifact IDs of the official types `REQ`, `DISC`, `PLAN`, `DES`, `ARCH`,
  `TASK`, `REV`, `QA`, `DEC`, `SUM`, and `CLAR` (three or more digits, such
  as `TASK-0123`);
- the store path `.factory-state` (ignore and attribute files such as
  `.gitignore` and `.dockerignore` may name the path, but not IDs).

Artifact IDs belong in `.factory-state/` and in PR titles and bodies, which
is how work is tracked. Factory-managed surfaces may reference artifacts:
`.factory-state/`, `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `project.md`,
`project-specs.md`, `vision.md`, `roadmap.md`, `.gitmodules`, tool kit
directories (`.agents/`, `.claude/`, `.codex/`, `.cursor/`, `.grok/`), and
pull request templates under `.github/`.

### English only, except i18n

Code, comments, docs, factory artifacts, templates, skills, commit messages,
and PR titles and bodies are written in English. Vietnamese is detected by
letters only Vietnamese uses among Latin scripts, after NFC normalization:
a with breve, o and u with horn, d with stroke (U+0103, U+01A1, U+01B0,
U+0111 and their capitals), and the tone-marked vowels of U+1EA0..U+1EF9.
Circumflex a, e, and o count only with a tone-marked vowel on the same line
and no letter Vietnamese never uses (cedilla, diaeresis, ring, n-tilde), so
French or Portuguese words are not reported. Detection is by letter, not by
word list.

Vietnamese is allowed in i18n surfaces:

- files under a directory named `locales`, `locale`, `i18n`, `l10n`,
  `translations`, `translation`, `lang`, or `langs`;
- files under a Vietnamese locale directory (`vi`, `vi-VN`, `vi_VN`, Android
  `values-vi`), for example `handbook/docs/vi/`;
- files with a Vietnamese locale or i18n token in the name: `vi.json`,
  `README.vi.md`, `mkdocs.vi.yml`, `messages_vi.properties`,
  `i18n.spec.ts`;
- translation catalog formats: `.po`, `.pot`, `.xliff`, `.xlf`, `.arb`,
  `.strings`, `.stringsdict`.

Legal and attribution files (`LICENSE*`, `COPYING*`, `NOTICE*`, `AUTHORS*`,
`CONTRIBUTORS*`) keep people's names verbatim and are not checked for
language. The language's own name, used by language switchers, is always
allowed.

### Scanned files

Inside a Git work tree whose root is the project, the scan covers tracked
and untracked files that `.gitignore` does not exclude; otherwise it walks
the directory. It always skips `.factory/` (the framework copy or
submodule), VCS metadata, dependency, build, and cache directories
(`node_modules`, `vendor`, `third_party`, `dist`, `build`, `out`, `target`,
`coverage`, `.venv`, `venv`, `__pycache__`, `.next`, `.nuxt`, `.svelte-kit`,
`.gradle`, `.dart_tool`, `Pods`, and similar), lockfiles, minified files,
source maps, snapshots, binary files, and files over 1 MiB.

### Project overrides

A project may extend the defaults in `.factory-state/hygiene.yaml`. Every key
is optional; patterns use `fnmatch` against the path relative to the project
root, and `*` also crosses `/`. A pattern without wildcards matches that file
or everything under that directory.

```yaml
i18n_paths:                 # Vietnamese allowed (inline catalogs, i18n tests)
  - "packages/mobile/src/labels.ts"
  - "frontend/e2e/*"
artifact_reference_paths:   # artifact IDs and store paths allowed
  - "docs/factory-notes.md"
skip_paths:                 # not scanned at all
  - "fixtures/third-party/*"
allowed_terms:              # proper names that keep their diacritics
  - "Owner Full Name"
```

Prefer moving text into a catalog over adding an override; an override is for
files that are i18n by nature, such as tests that assert translated output.

### Pull request text

A working tree cannot see GitHub PR text. `factory pr check` checks a PR
title and body for Vietnamese: from `--title` and `--body`/`--body-file`, or
from the GitHub event payload in `--event` or `$GITHUB_EVENT_PATH`.
`factory validate` also checks the PR in `$GITHUB_EVENT_PATH` when it holds a
pull request event. Copy `templates/ci/factory-pr-text.yml` so edits to a PR
title or body are rechecked.

## Agent Handoffs

- Every handoff must be file-based.
- Every artifact must identify related inputs.
- Every assumption must be documented.
- Every blocked item must identify the missing decision, artifact, or approval.
