# Migration To 0.3

Version 0.3 adds source scaffolding, dependency workflows, deterministic verification, stack configurators, and an installable CLI inside new `.factory` copies.

## Upgrade The Operator CLI

Use a virtual environment rather than the externally managed system Python:

```text
cd <factory-repository>
git pull
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/factory --help
```

## Update Project Factory Assets

Projects using a submodule should review and update its revision normally:

```text
git submodule update --init .factory
git -C .factory fetch
git -C .factory checkout <reviewed-0.3-revision>
git add .factory
```

Projects using a detached copy from an earlier release can continue existing artifact workflows, but generated CI requires `.factory/pyproject.toml`, `.factory/cli/`, and `.factory/bin/`. Copy those three assets from a reviewed 0.3 Factory checkout, review the diff, and commit them with the project migration. Do not replace project-owned `.factory-state/`.

## Revalidate

```text
factory validate .
factory tools validate -C .
factory deps validate -C .           # when dependency state exists
factory verify validate -C .         # after the first verification run
```

## Behavioral Changes

- GitHub Actions generation uses current official setup actions and supports Flutter through the official stable SDK repository.
- GitLab CI generation requires the owner-operated runner to provide all approved stack runtimes.
- Database configuration includes a local `DATABASE_URL` contract but does not select or install an application ORM or driver.
- Approved cloud and deployment choices produce readiness warnings until project-specific account, region, network, state, runtime, rollout, rollback, and credential decisions exist.
