# Project Dependency Installation

Factory installs project-local dependencies from manifests and lockfiles already in the repository. Package-manager execution is its own transaction because network operations cannot be rolled back reliably.

## Flow

```text
dependency discovery and exact command preview
        ↓
network approval via --allow-network
        ↓
project-local package-manager commands
        ↓
installed.yaml or INCOMPLETE
        ↓
dependency validation
```

Scripts and CI select the install explicitly:

The phase can be planned, retried, and validated independently:

```text
factory deps plan -C <project-dir>
factory deps apply -C <project-dir> --allow-network
factory deps validate -C <project-dir>
```

## Supported Manifests And Managers

| Evidence | Selected command |
| --- | --- |
| `package-lock.json` | `npm ci --include=dev` |
| `pnpm-lock.yaml` | `pnpm install --frozen-lockfile` |
| `yarn.lock` | `yarn install --frozen-lockfile` |
| `bun.lock` or `bun.lockb` | `bun install --frozen-lockfile` |
| `package.json` without a lockfile | Declared `packageManager`, or npm only when scaffold provenance identifies a built-in Node adapter; npm uses `install --include=dev` |
| `pyproject.toml` with `uv.lock` | `uv sync --locked` |
| `pyproject.toml` without `uv.lock` | Create local `.venv`, then editable install; include the `test` extra when declared |
| `requirements.txt` without a sibling `pyproject.toml` | Create local `.venv`, then `.venv` pip `install -r requirements.txt` |
| `pubspec.yaml` | `flutter pub get` |
| `pom.xml` | Project Maven wrapper, or `mvn`, with `dependency:go-offline` |
| `*.csproj` | `dotnet restore <project>` |
| `go.mod` | `go mod download` |

A single lockfile provides the strongest package-manager evidence. Multiple manager lockfiles, or a lockfile that disagrees with `packageManager`, are planning errors. An imported Node project with neither a lockfile nor a valid `packageManager` is also ambiguous. Factory does not guess npm for unknown repositories.

Factory looks for manifests throughout the project while excluding `.git/`, `.factory/`, `.factory-state/`, existing `.venv/`, `node_modules/`, and Flutter's `.dart_tool/`.

## Tool Ownership

Factory invokes local executables but does not bootstrap the runtimes or package managers themselves. The owner installs prerequisites such as Node.js with npm/npx, pnpm, Yarn, Bun, `uv`, Java/Maven, the .NET SDK, Go, or the Flutter SDK before applying the plan. A missing executable makes the plan unavailable and does not trigger a global install.

Python fallback uses a `.venv` beside the Python manifest. Built-in Python scaffold providers publish a matching `.gitignore` entry before this phase. Imported projects remain responsible for ignoring their local environment. Factory never writes into Homebrew or another externally managed Python environment, never uses `--break-system-packages`, and never installs with a global pip.

## Review And Network Boundary

`factory deps plan` is read-only and shows every command, working directory, manager, and network requirement. Interactive apply uses a Markdown review; accepting it grants network access for the displayed plan. Non-interactive apply refuses network-dependent commands unless `--allow-network` is present.

Commands are passed to subprocesses as argument arrays rather than through a shell. Factory sets non-interactive and no-color environment hints, captures the observed exit status, and enforces a timeout. If any dependency manifest or lockfile changes after planning, execution stops before the first command.

For npm projects, Factory explicitly includes development dependencies because local serve, build, test, lint, and typecheck commands commonly depend on them. A successful install is followed by `npm ls --depth=0 --include=dev`; missing declared dependencies or development dependencies make the installation incomplete.

## Provenance, Failure, And Retry

A successful apply records `.factory-state/dependencies/installed.yaml` with:

- input manifest and lockfile hashes;
- the argument arrays and working directories, with an absolute executable
  recorded by its name (`npm`, not `/usr/local/bin/npm`) so the file is the
  same on every machine;
- managers and expected project-local outputs;
- timestamps, exit statuses, and completion status.

If a command fails, already-published source remains untouched. Factory records the partial command evidence and writes `.factory-state/dependencies/INCOMPLETE`. Fix the runtime, credentials, registry, or manifest issue, then run `factory deps plan` and `factory deps apply` again. A later success removes the marker.

`factory deps validate` fails for incomplete or missing dependency state, missing expected environments, and missing top-level npm dependencies declared by `package.json`. Legacy npm state without integrity evidence produces a warning and can be refreshed by rerunning `factory deps apply`. Manifest or lockfile drift is reported as a warning so the owner can deliberately rerun installation. Build output and caches (`dist/`, `build/`, `coverage/`, `.next/`, `.svelte-kit/`) are not searched for manifests, so a `package.json` a build copies there is not drift. The top-level `factory validate` includes dependency checks only after dependency state exists.

## Boundaries

This workflow installs dependencies already declared by scaffolded or imported manifests. It does not choose libraries, add feature dependencies, manage credentials, configure private registries, install global tooling, run database migrations, or claim that application tests pass. Those remain explicit implementation and validation tasks.
