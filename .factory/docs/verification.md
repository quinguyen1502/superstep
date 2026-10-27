# Project Verification

`factory verify` runs the verification commands declared in
`.factory-state/tooling/tool-policy.yaml`. It does not execute free-text
commands from project intake, and it does not ask a model to invent commands.

## Flow

```text
factory verify plan -C <project-dir> --profile quick
factory verify run -C <project-dir> --profile full
factory verify validate -C <project-dir>
```

`plan` is read-only. `run` executes the reviewed checks and writes
`.factory-state/verification/latest.yaml`. `validate` reads that file.

Use repeated `--check` flags to narrow a plan to `check`, `test`, `lint`,
`typecheck`, `build`, `format`, or `analyze`. The `quick` profile excludes
`build`; `full` includes it.

## Command Source

A command is a verification command when its `kind` is one of those names,
or when `kind` is omitted and the command name itself is one of them.
`install` and `run` stay in the policy and are not executed by verify.

```yaml
commands:
  test:
    command: .venv/bin/python -m pytest
    cwd: backend
    timeout: 900
    evidence: Expected
  frontend-lint:
    command: npm run lint
    cwd: frontend
    kind: lint
    evidence: Expected
```

`cwd` is a relative directory. `command` is an argument list, not a shell
script: Factory does not interpret pipes or `&&`. The first argument is a
command name on `PATH`, or a relative path such as `.venv/bin/python`.
Absolute paths are rejected.

Each command may run for 300 seconds. A slow suite sets its own `timeout`
in seconds, as `test` does above. `factory verify run --timeout SECONDS`
changes the limit for commands without one, for example on a slower
machine. A command that runs out of time fails and says which setting to
raise.

When the policy file exists but declares no verification commands, `plan`
discovers checks from project manifests and `run` records that full set into
the policy. The policy is then the only source. A later manifest script does
not become a check until the policy lists it. When the policy file is absent,
discovery is used for that run and nothing is written back.

Recorded names are `<dir>-<kind>`, or `<kind>` at the project root. When two
checks would share a name, such as npm and pytest tests at the root, or the
policy already uses the name for another command, the later one gets the tool
as well (`test-python`), then a number.

| Evidence | Checks recorded into an empty policy |
| --- | --- |
| Node `package.json` scripts | `test`, `lint`, `typecheck`/`type-check`, `build` |
| Django `manage.py` with a project-local Python environment | `check`, `test` |
| Python test/lint/typecheck dependencies | pytest or unittest, Ruff, mypy, or Pyright |
| Flutter `pubspec.yaml` | `flutter analyze`, `flutter test` |
| Maven `pom.xml` | test and package build |
| .NET project files | test and build |
| Go module | vet, test, and build |

Node package-manager selection uses manifest declarations, lockfiles, or
managed scaffold provenance. Python checks require the project-local
`.venv`; Factory does not fall back to the system interpreter.

## Evidence

`latest.yaml` stores the profile, each portable command, the relative working
directory, the exit code, and pass or fail. It does not store absolute
executable paths, per-file input hashes, output hashes, or timestamps, so
running the same checks again leaves the file unchanged.

Raw command output is printed for diagnosis and is not stored. Timestamped
copies under `.factory-state/verification/runs/` are no longer written.
`factory gc --apply` deletes any that are already there (`--no-tasks` does only
that). `latest.yaml` stays.

Older evidence that still contains input hashes or absolute paths remains
valid. `factory validate` warns until `factory verify run` replaces it.
`factory validate` includes verification only after verification state exists;
`factory verify validate` requires that state explicitly.

Verification commands are expected to be non-mutating, but build and test
tools may create ordinary caches or build outputs.
