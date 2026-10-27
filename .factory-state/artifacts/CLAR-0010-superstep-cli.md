---
schema_version: 1
id: CLAR-0010
task_id: REQ-0079
status: answered
source_artifacts:
  - .factory-state/artifacts/REQ-0079-superstep-cli.md
  - .factory-state/artifacts/REQ-0008-postgres-redis-compose.md
  - .factory-state/artifacts/REQ-0042-workflow-tests.md
  - .factory-state/artifacts/REQ-0070-workflows-as-mcp-tools.md
  - docs/deploy/README.md
created: 2026-10-27
updated: 2026-10-27
answered_at: '2026-10-27'
questions:
  - id: packaging
    type: single_choice
    prompt: How is the CLI built and installed?
    required: true
    context: >-
      Python is the server's language. The CLI could reuse the SDK's client, the MCP Python SDK for the stdio bridge,
      and the repository's tests and release workflow. uv or pipx install it in one command, and a one-line install.sh
      can install uv when Python is missing. A Go binary needs no runtime and runs natively on Windows, but it brings a
      new language, toolchain and client code to keep in step with the API. A Node package (npx) suits people who
      already have Node, but servers rarely do.
    recommendation: python
    options:
      - value: python
        label: >-
          Python: a `superstep` command in the `superstep` package (`cli` extra), installed with uv or pipx or a
          one-line install.sh; macOS and Linux, Windows through WSL
      - value: go-binary
        label: A Go binary for macOS, Linux and Windows, from GitHub Releases and Homebrew
      - value: node
        label: A Node package run with npx, next to the TypeScript SDK
  - id: first-version
    type: single_choice
    prompt: What goes in the first version?
    required: true
    context: >-
      The requirement has two halves: running an instance (install, upgrade, backup, status, doctor, admin, SSH
      deploy) and working with workflows (login, pull and push, run, test in CI, MCP over stdio). Each half is several
      tasks. Shipping the instance half first solves install and upgrade, what was asked for, and the workflow half
      follows in the next release. Shipping both together delays both.
    recommendation: phased
    options:
      - value: phased
        label: Two phases, the instance commands first and the workflow commands in the next release
      - value: all-at-once
        label: Both halves in one release
      - value: instance-only
        label: Only the instance commands; the workflow commands are dropped
  - id: topologies
    type: single_choice
    prompt: Which topologies does `superstep install` offer?
    required: true
    context: >-
      The single image with SQLite is the smallest install and fits one team. The full Compose stack (Postgres,
      Redis, a worker, nginx, and optionally the Docker sandbox for Code nodes) is what larger installs need. Both
      already exist as Compose files. Offering both, with the single image as the default, covers every current
      install path.
    recommendation: single-default-and-full
    options:
      - value: single-default-and-full
        label: Both; the single image by default, the full stack (with the sandbox as an option) on request
      - value: full-only
        label: Only the full stack
      - value: single-only
        label: Only the single image
  - id: deploy-targets
    type: single_choice
    prompt: Where can `superstep deploy` deploy?
    required: true
    context: >-
      Any Docker host over SSH covers VPSs and Coolify or Dokploy servers, with nothing but Docker on the server.
      Fly.io, Render, Railway, Zeabur and Heroku already have one-click configs in the repository, so a CLI wrapper adds
      little and depends on each platform's own CLI. Kubernetes would need a Helm chart, which does not exist yet.
    recommendation: ssh
    options:
      - value: ssh
        label: A Docker host over SSH
      - value: ssh-and-paas
        label: A Docker host over SSH, plus Fly.io, Render and Railway through their CLIs
      - value: ssh-paas-helm
        label: SSH, the platforms, and Kubernetes with a new Helm chart
  - id: rollback
    type: single_choice
    prompt: What does `superstep upgrade` do when the new version fails its health check?
    required: true
    context: >-
      Migrations only go forward, so going back means the previous version and the backup taken before the upgrade.
      Doing it automatically brings the instance back up without anyone at the keyboard, and the failed upgrade's logs
      are kept. Asking first suits an operator watching the upgrade, but leaves the instance down until they answer.
      Leaving it to the operator is the least work, but it is what the CLI is meant to remove.
    recommendation: automatic
    options:
      - value: automatic
        label: Restore the backup and the previous version automatically, and keep the failed upgrade's logs
      - value: ask
        label: Ask the operator, and restore only if they agree
      - value: manual
        label: Stop and print the restore command
  - id: scheduled-backups
    type: single_choice
    prompt: Can the CLI schedule backups?
    required: true
    context: >-
      `superstep backup --schedule daily --keep 7` could install a systemd timer (or cron where systemd is missing) on
      the host and prune old archives. A backup container inside the Compose stack would work on hosts without
      systemd, but it is one more service. Without either, the docs show a cron line.
    recommendation: host-timer
    options:
      - value: host-timer
        label: Yes, with a systemd timer or cron on the host, keeping the last N archives
      - value: compose-service
        label: Yes, with a backup service in the Compose stack
      - value: docs-only
        label: No, the docs show a cron line
  - id: auth
    type: single_choice
    prompt: How do the workflow commands sign in?
    required: true
    context: >-
      Workflow tokens (REQ-0004) can only run one workflow, so pull, push, test and listing need a user-level
      credential. A personal access token, made through a browser sign-in (`superstep login` opens the studio, the user
      approves, and the CLI gets a token), works with SSO-like setups, never handles the password, and can be revoked
      in Settings. In CI, a token is made in Settings and passed as `SUPERSTEP_TOKEN`. Signing in with a password is
      simpler, but then the CLI stores a session and handles the password.
    recommendation: pat-browser
    options:
      - value: pat-browser
        label: Personal access tokens, from a browser sign-in or from Settings for CI
      - value: password
        label: E-mail and password, with the CLI keeping a session
      - value: workflow-tokens
        label: Only workflow tokens; pull, push and test are left out
  - id: versioning
    type: single_choice
    prompt: How is the CLI versioned and released?
    required: true
    context: >-
      Releasing the CLI with every Superstep tag, under the same version, makes `superstep upgrade` and the "versions
      far apart" warning simple, and the CLI's install templates always match a release. Its own version and tags
      (like the SDKs' `sdk-py-v*`) let it change without a server release, but the CLI would then need to know which
      server versions it supports.
    recommendation: same-as-server
    options:
      - value: same-as-server
        label: The same version as the server, released on each `v*` tag
      - value: own-version
        label: Its own version and tags, with a list of the server versions it supports
answers:
  packaging: python
  first-version: phased
  topologies: single-default-and-full
  deploy-targets: ssh
  rollback: automatic
  scheduled-backups: host-timer
  auth: pat-browser
  versioning: same-as-server
---
# Clarification

Owner questions for REQ-0079, the `superstep` command-line tool. The owner answered in chat on 2026-10-27 ("Làm theo
đề xuất") and picked the recommended option for every question. The answers are written into REQ-0079 under Owner
Decisions.
