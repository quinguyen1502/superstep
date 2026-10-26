from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Dict, Iterable, List, Mapping, Sequence

from ..models import ProjectIntake
from ..stacks import find_stack
from .models import ConfigurationOutput


class ConfigurationError(Exception):
    """Blocking stack configuration planning or publication problem."""


@dataclass(frozen=True)
class ConfigurationContext:
    intake: ProjectIntake
    approved: Mapping[str, str]
    integration_branch: str = "develop"
    factory_cli_available: bool = False

    def stack_id(self, area: str) -> str:
        value = self.approved.get(area, "")
        stack = find_stack(area, value)
        return stack.stack_id if stack else ""


class StackConfigurator:
    configurator_id = ""

    def matches(self, context: ConfigurationContext) -> bool:
        raise NotImplementedError

    def validate(self, context: ConfigurationContext) -> Sequence[str]:
        return ()

    def warnings(self, context: ConfigurationContext) -> Sequence[str]:
        return ()

    def render(self, context: ConfigurationContext) -> Sequence[ConfigurationOutput]:
        raise NotImplementedError


class DatabaseComposeConfigurator(StackConfigurator):
    configurator_id = "database-compose"
    SUPPORTED = {"postgresql", "mysql", "mongodb"}

    def matches(self, context: ConfigurationContext) -> bool:
        return context.stack_id("database") in self.SUPPORTED

    def validate(self, context: ConfigurationContext) -> Sequence[str]:
        if context.stack_id("infrastructure") != "docker-compose":
            return (
                "database service configuration requires Approved infrastructure: "
                "Docker Compose",
            )
        return ()

    def warnings(self, context: ConfigurationContext) -> Sequence[str]:
        return (
            "database service files do not wire an application driver, ORM, migrations, "
            "or production credentials",
        )

    def render(self, context: ConfigurationContext) -> Sequence[ConfigurationOutput]:
        database = context.stack_id("database")
        compose, environment = _database_files(database)
        return (
            ConfigurationOutput(
                "compose.database.yaml", compose.encode("utf-8"), self.configurator_id
            ),
            ConfigurationOutput(
                ".env.database.example",
                environment.encode("utf-8"),
                self.configurator_id,
            ),
        )


class GitHubActionsConfigurator(StackConfigurator):
    configurator_id = "github-actions-verify"

    def matches(self, context: ConfigurationContext) -> bool:
        return context.stack_id("ci_cd") == "github-actions"

    def validate(self, context: ConfigurationContext) -> Sequence[str]:
        if not context.factory_cli_available:
            return (
                "GitHub Actions requires an installable Factory CLI at .factory; "
                "update or re-import the Factory copy/submodule before publishing CI",
            )
        return ()

    def warnings(self, context: ConfigurationContext) -> Sequence[str]:
        if context.stack_id("mobile") == "flutter":
            return (
                "GitHub Actions installs Flutter from the official stable channel at "
                "runtime; pin a reviewed SDK revision if exact reproducibility is required",
            )
        return ()

    def render(self, context: ConfigurationContext) -> Sequence[ConfigurationOutput]:
        content = _github_actions_workflow(context)
        return (
            ConfigurationOutput(
                ".github/workflows/factory-verify.yml",
                content.encode("utf-8"),
                self.configurator_id,
            ),
        )


class GitLabCiConfigurator(StackConfigurator):
    configurator_id = "gitlab-ci-verify"

    def matches(self, context: ConfigurationContext) -> bool:
        return context.stack_id("ci_cd") == "gitlab-ci"

    def validate(self, context: ConfigurationContext) -> Sequence[str]:
        if not context.factory_cli_available:
            return (
                "GitLab CI requires an installable Factory CLI at .factory; "
                "update or re-import the Factory copy/submodule before publishing CI",
            )
        return ()

    def warnings(self, context: ConfigurationContext) -> Sequence[str]:
        return (
            "GitLab runners must provide the approved stack runtimes: "
            + ", ".join(_required_runtime_names(context)),
        )

    def render(self, context: ConfigurationContext) -> Sequence[ConfigurationOutput]:
        return (
            ConfigurationOutput(
                ".gitlab-ci.yml",
                _gitlab_ci_workflow(context).encode("utf-8"),
                self.configurator_id,
            ),
        )


BUILTIN_CONFIGURATORS: Sequence[StackConfigurator] = (
    DatabaseComposeConfigurator(),
    GitHubActionsConfigurator(),
    GitLabCiConfigurator(),
)


def approved_choices(intake: ProjectIntake) -> Dict[str, str]:
    return {
        area: choice.value.strip()
        for area, choice in intake.tech_stack.items()
        if choice.status == "Approved" and choice.value.strip()
    }


def matching_configurators(
    context: ConfigurationContext,
    configurators: Iterable[StackConfigurator] = BUILTIN_CONFIGURATORS,
) -> List[StackConfigurator]:
    return [configurator for configurator in configurators if configurator.matches(context)]


def _database_files(database: str) -> tuple[str, str]:
    if database == "postgresql":
        return (
            """services:
  database:
    image: ${POSTGRES_IMAGE:-postgres:17-alpine}
    restart: unless-stopped
    ports:
      - \"${DATABASE_PORT:-5432}:5432\"
    environment:
      POSTGRES_DB: ${DATABASE_NAME:-app}
      POSTGRES_USER: ${DATABASE_USER:-app}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD:-change-me}
    volumes:
      - database-data:/var/lib/postgresql/data
    healthcheck:
      test: [\"CMD-SHELL\", \"pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB\"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  database-data:
""",
            """POSTGRES_IMAGE=postgres:17-alpine
DATABASE_PORT=5432
DATABASE_NAME=app
DATABASE_USER=app
DATABASE_PASSWORD=change-me
DATABASE_URL=postgresql://app:change-me@localhost:5432/app
""",
        )
    if database == "mysql":
        return (
            """services:
  database:
    image: ${MYSQL_IMAGE:-mysql:8.4}
    restart: unless-stopped
    ports:
      - \"${DATABASE_PORT:-3306}:3306\"
    environment:
      MYSQL_DATABASE: ${DATABASE_NAME:-app}
      MYSQL_USER: ${DATABASE_USER:-app}
      MYSQL_PASSWORD: ${DATABASE_PASSWORD:-change-me}
      MYSQL_ROOT_PASSWORD: ${DATABASE_ROOT_PASSWORD:-change-me-root}
    volumes:
      - database-data:/var/lib/mysql
    healthcheck:
      test: [\"CMD\", \"mysqladmin\", \"ping\", \"-h\", \"localhost\"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  database-data:
""",
            """MYSQL_IMAGE=mysql:8.4
DATABASE_PORT=3306
DATABASE_NAME=app
DATABASE_USER=app
DATABASE_PASSWORD=change-me
DATABASE_ROOT_PASSWORD=change-me-root
DATABASE_URL=mysql://app:change-me@localhost:3306/app
""",
        )
    if database == "mongodb":
        return (
            """services:
  database:
    image: ${MONGO_IMAGE:-mongo:8.0}
    restart: unless-stopped
    ports:
      - \"${DATABASE_PORT:-27017}:27017\"
    environment:
      MONGO_INITDB_DATABASE: ${DATABASE_NAME:-app}
      MONGO_INITDB_ROOT_USERNAME: ${DATABASE_USER:-app}
      MONGO_INITDB_ROOT_PASSWORD: ${DATABASE_PASSWORD:-change-me}
    volumes:
      - database-data:/data/db
    healthcheck:
      test: [\"CMD\", \"mongosh\", \"--eval\", \"db.adminCommand('ping')\"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  database-data:
""",
            """MONGO_IMAGE=mongo:8.0
DATABASE_PORT=27017
DATABASE_NAME=app
DATABASE_USER=app
DATABASE_PASSWORD=change-me
DATABASE_URL=mongodb://app:change-me@localhost:27017/app?authSource=admin
""",
        )
    raise ConfigurationError(f"Unsupported database configurator target: {database}")


def _github_actions_workflow(context: ConfigurationContext) -> str:
    steps = [
        "      - uses: actions/checkout@v6\n        with:\n          submodules: recursive",
        "      - uses: actions/setup-python@v6\n        with:\n          python-version: '3.12'",
    ]
    approved_ids = {
        context.stack_id("frontend"),
        context.stack_id("backend"),
    }
    node_ids = {
        "react-typescript-vite",
        "vue-typescript-vite",
        "angular-typescript",
        "nextjs",
        "sveltekit",
        "node-nestjs",
    }
    if approved_ids & node_ids:
        steps.append(
            "      - uses: actions/setup-node@v6\n"
            "        with:\n          node-version: '22'"
        )
    if "java-spring-boot" in approved_ids:
        steps.append(
            "      - uses: actions/setup-java@v5\n"
            "        with:\n          distribution: temurin\n          java-version: '21'"
        )
    if "aspnet-core-webapi" in approved_ids:
        steps.append(
            "      - uses: actions/setup-dotnet@v5\n"
            "        with:\n          dotnet-version: '10.0.x'"
        )
    if "go-gin-rest" in approved_ids:
        steps.append(
            "      - uses: actions/setup-go@v6\n"
            "        with:\n          go-version: '1.25.x'"
        )
    if context.stack_id("mobile") == "flutter":
        steps.extend(
            (
                "      - name: Install Flutter SDK\n"
                "        run: |\n"
                "          git clone https://github.com/flutter/flutter.git "
                "--depth 1 --branch stable \"${RUNNER_TEMP}/flutter\"\n"
                "          echo \"${RUNNER_TEMP}/flutter/bin\" >> \"${GITHUB_PATH}\"",
                "      - name: Verify Flutter SDK\n        run: flutter --version",
            )
        )
    steps.extend(
        (
            "      - name: Install Factory CLI\n"
            "        run: python -m pip install ./.factory",
            "      - name: Install project dependencies\n"
            "        run: factory deps apply --allow-network",
            "      - name: Verify project\n"
            "        run: factory verify run --profile full",
        )
    )
    return (
        """name: Factory verification

on:
  pull_request:
  push:
    branches: [{integration_branch}]

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
""".format(integration_branch=json.dumps(context.integration_branch))
        + "\n".join(steps)
        + "\n"
    )


def _required_runtime_names(context: ConfigurationContext) -> List[str]:
    stack_ids = {
        context.stack_id("frontend"),
        context.stack_id("mobile"),
        context.stack_id("backend"),
    }
    runtimes = ["Python 3 with venv"]
    if stack_ids & {
        "react-typescript-vite",
        "vue-typescript-vite",
        "angular-typescript",
        "nextjs",
        "sveltekit",
        "node-nestjs",
    }:
        runtimes.append("Node.js 22 with the selected package manager")
    if "java-spring-boot" in stack_ids:
        runtimes.append("Java 21")
    if "aspnet-core-webapi" in stack_ids:
        runtimes.append(".NET SDK 10")
    if "go-gin-rest" in stack_ids:
        runtimes.append("Go 1.25")
    if "flutter" in stack_ids:
        runtimes.append("Flutter stable SDK")
    return runtimes


def _gitlab_ci_workflow(context: ConfigurationContext) -> str:
    runtime_comment = ", ".join(_required_runtime_names(context))
    return f"""# Required runner tools: {runtime_comment}
stages:
  - verify

variables:
  PIP_DISABLE_PIP_VERSION_CHECK: "1"
  PYTHONDONTWRITEBYTECODE: "1"

factory-verify:
  stage: verify
  before_script:
    - python3 -m venv /tmp/factory-cli-venv
    - /tmp/factory-cli-venv/bin/python -m pip install ./.factory
  script:
    - /tmp/factory-cli-venv/bin/factory deps apply --allow-network
    - /tmp/factory-cli-venv/bin/factory verify run --profile full
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH'
"""
