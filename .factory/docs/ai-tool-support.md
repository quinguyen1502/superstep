# AI Coding Tool Support

Factory workflows and artifacts are tool-neutral. Tool adapters translate only the instruction and optional specification-refinement boundaries.

## Canonical Instructions

- `AGENTS.md` is the canonical project entrypoint for Codex, Cursor, and Grok.
- `.claude/CLAUDE.md` imports `@../AGENTS.md` for Claude Code.
- `.factory/AGENTS.md` remains the required shared framework instruction source.
- `.factory-state/factory.yaml` records enabled tools and the owner-selected default refiner.
- `.factory-state/tooling/tool-policy.yaml` is the canonical source for project-local permissions and hooks.

Do not duplicate the entire instruction set into provider-specific files. Factory can derive reviewed Codex and Claude Code permissions and hooks from the canonical tool policy. Cursor and Grok continue to use `AGENTS.md`; Factory does not generate native Cursor or Grok permission files by default. Grok skills are emitted to `.grok/skills/`.

Provider configuration is never silently activated. The default `instructions` kit remains inactive. Active kit files are previewed, existing files are preserved, and conflicts become owner-reviewed proposals. Factory does not manage home-directory configuration, authentication, model selection, telemetry, provider endpoints, or permission-bypass flags.

## Refinement Safety

Adapters receive only staged intake and template files. They must return normalized JSON with `markdown`, `assumptions`, and `open_questions`. They must not publish project files or silently approve technology choices.

Missing executables, authentication failures, timeouts, and malformed output fall back to the deterministic draft. Factory never switches providers without an owner choice.

## Creating A Project From An Agent

From the factory repository, an agent can create a project without the wizard:

```bash
factory init <name> --no-interactive \
  [--intake FILE.yaml] [--from-specs FILE.md] [--preset web-app|api|cli|mobile] \
  [--tool grok]
```

`--intake` loads a `ProjectIntake` YAML. `--from-specs` publishes owner-written
specs and fills blank intake fields. `--preset` fills remaining blank stack and
command fields as `Proposed` only. Skills are emitted by default; pass
`--no-skills` to skip.

A created project is valid (`factory validate`) before it is ready for
implementation (`factory ready`).

## Branch Names

New task branches use the tool-neutral convention `factory/task-<id>-<short-name>`. Existing `codex/task-*` branches remain historical and valid.
