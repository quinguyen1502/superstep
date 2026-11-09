# CI workflow

Factory ships a static GitHub Actions workflow at
`templates/ci/factory-verify.yml`. In a project that links the framework,
the same file is `.factory/templates/ci/factory-verify.yml`.

Copy it into the project and edit it there:

```bash
mkdir -p .github/workflows
cp .factory/templates/ci/factory-verify.yml .github/workflows/factory-verify.yml
```

The workflow checks out submodules, installs the Factory CLI from
`.factory`, runs `factory validate --only hygiene` (artifact isolation,
English-only text, and the PR title and body on pull request events),
installs project dependencies, and runs `factory verify run --profile full`. Set `branches` to the integration
branch. Add runtime setup for Node, Java, .NET, Go, or Flutter before
the Factory CLI install when the project needs those tools.

`templates/ci/factory-pr-text.yml` reruns `factory pr check` when a PR is
opened, edited, reopened, or synchronized, so a title or body edited after
the last push is still checked:

```bash
cp .factory/templates/ci/factory-pr-text.yml .github/workflows/factory-pr-text.yml
```

Factory does not generate Compose files, GitLab CI, or hashed copies of
the workflow. An existing `.factory-state/configuration/` directory from
an older release is unused. `factory validate` does not read it.
