from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple


CAPABILITY_LABELS = {
    "scaffold": "scaffold",
    "dependencies": "dependencies",
    "verify": "verify",
    "configuration": "configuration",
}


@dataclass(frozen=True)
class StackDefinition:
    stack_id: str
    area: str
    label: str
    description: str
    capabilities: Tuple[str, ...] = ()
    adapter_id: Optional[str] = None
    prerequisites: Tuple[str, ...] = ()
    aliases: Tuple[str, ...] = ()

    def matches(self, value: str) -> bool:
        normalized = value.strip().casefold()
        return normalized in {
            candidate.casefold() for candidate in (self.label, *self.aliases)
        }

    @property
    def option_label(self) -> str:
        capabilities = [
            CAPABILITY_LABELS[item]
            for item in self.capabilities
            if item in CAPABILITY_LABELS
        ]
        suffix = " + ".join(capabilities) if capabilities else "specification only"
        return f"{self.label} · {suffix}"

    @property
    def capability_summary(self) -> str:
        if not self.capabilities:
            return "Factory records this choice in specifications but has no automation adapter yet."
        rendered = ", ".join(
            CAPABILITY_LABELS.get(item, item) for item in self.capabilities
        )
        summary = f"Factory capabilities: {rendered}."
        if self.prerequisites:
            summary += " Prerequisites: " + ", ".join(self.prerequisites) + "."
        return summary


STACK_DEFINITIONS: Tuple[StackDefinition, ...] = (
    StackDefinition(
        "react-typescript-vite",
        "frontend",
        "React + TypeScript",
        "React client application generated with Vite.",
        ("scaffold", "dependencies", "verify"),
        "vite",
        ("Node.js with npm",),
    ),
    StackDefinition(
        "vue-typescript-vite",
        "frontend",
        "Vue + TypeScript",
        "Vue client application generated with Vite.",
        ("scaffold", "dependencies", "verify"),
        "vite",
        ("Node.js with npm",),
    ),
    StackDefinition(
        "angular-typescript",
        "frontend",
        "Angular + TypeScript",
        "Angular standalone application generated with the official Angular CLI.",
        ("scaffold", "dependencies", "verify"),
        "angular",
        ("Node.js with npx",),
    ),
    StackDefinition(
        "nextjs",
        "frontend",
        "Next.js",
        "Next.js application using the App Router and TypeScript.",
        ("scaffold", "dependencies", "verify"),
        "nextjs",
        ("Node.js with npx",),
    ),
    StackDefinition(
        "sveltekit",
        "frontend",
        "SvelteKit",
        "SvelteKit application generated with the official Svelte CLI.",
        ("scaffold", "dependencies", "verify"),
        "sveltekit",
        ("Node.js with npx",),
    ),
    StackDefinition(
        "flutter",
        "mobile",
        "Flutter",
        "Cross-platform mobile application generated with the Flutter SDK.",
        ("scaffold", "dependencies", "verify"),
        "flutter",
        ("Flutter SDK for local workflows; GitHub CI installs the stable SDK",),
    ),
    StackDefinition(
        "react-native",
        "mobile",
        "React Native",
        "Cross-platform React Native application.",
    ),
    StackDefinition("swiftui", "mobile", "SwiftUI", "Native Apple application."),
    StackDefinition(
        "kotlin-compose",
        "mobile",
        "Kotlin Compose",
        "Native or multiplatform Kotlin Compose application.",
    ),
    StackDefinition(
        "mobile-not-applicable",
        "mobile",
        "Not applicable",
        "No dedicated mobile application is planned.",
    ),
    StackDefinition(
        "python-fastapi-rest",
        "backend",
        "Python + FastAPI + REST",
        "Factory-maintained FastAPI REST baseline.",
        ("scaffold", "dependencies", "verify"),
        "fastapi-template",
        ("Python 3.9+",),
    ),
    StackDefinition(
        "python-django",
        "backend",
        "Python + Django",
        "Django project generated with django-admin or the current Python environment.",
        ("scaffold", "dependencies", "verify"),
        "django",
        ("Python 3.9+ with Django",),
    ),
    StackDefinition(
        "python-cli",
        "backend",
        "Python CLI",
        "Factory-maintained Python command-line application baseline.",
        ("scaffold", "dependencies", "verify"),
        "python-cli-template",
        ("Python 3.9+",),
    ),
    StackDefinition(
        "node-nestjs",
        "backend",
        "Node.js + NestJS",
        "NestJS API generated with the official Nest CLI.",
        ("scaffold", "dependencies", "verify"),
        "nestjs",
        ("Node.js with npx",),
    ),
    StackDefinition(
        "java-spring-boot",
        "backend",
        "Java + Spring Boot",
        "Spring Web API generated through Spring Initializr.",
        ("scaffold", "dependencies", "verify"),
        "spring-boot",
        ("Java and Spring Boot CLI", "network access to Spring Initializr"),
    ),
    StackDefinition(
        "aspnet-core-webapi",
        "backend",
        "ASP.NET Core Web API",
        "Minimal ASP.NET Core Web API generated with the .NET SDK.",
        ("scaffold", "dependencies", "verify"),
        "aspnet-core",
        (".NET SDK",),
    ),
    StackDefinition(
        "go-gin-rest",
        "backend",
        "Go + Gin REST",
        "Factory-maintained REST baseline using Gin.",
        ("scaffold", "dependencies", "verify"),
        "go-gin-template",
        ("Go 1.25+",),
        ("Go + REST",),
    ),
    StackDefinition(
        "postgresql",
        "database",
        "PostgreSQL",
        "Relational database with strong transactional and extension support.",
        ("configuration",),
        prerequisites=("Docker Compose for the v1 service configurator",),
    ),
    StackDefinition(
        "mysql",
        "database",
        "MySQL",
        "Relational database commonly paired with framework ORM adapters.",
        ("configuration",),
        prerequisites=("Docker Compose for the v1 service configurator",),
    ),
    StackDefinition(
        "sqlite",
        "database",
        "SQLite",
        "Embedded relational database suited to local and single-instance workloads.",
    ),
    StackDefinition(
        "mongodb",
        "database",
        "MongoDB",
        "Document database requiring a framework-specific driver or ODM decision.",
        ("configuration",),
        prerequisites=("Docker Compose for the v1 service configurator",),
    ),
    StackDefinition(
        "database-not-applicable",
        "database",
        "Not applicable",
        "No persistent application database is planned.",
    ),
    StackDefinition(
        "aws-terraform",
        "infrastructure",
        "AWS + Terraform",
        "AWS infrastructure declared through Terraform.",
    ),
    StackDefinition(
        "gcp-terraform",
        "infrastructure",
        "Google Cloud + Terraform",
        "Google Cloud infrastructure declared through Terraform.",
    ),
    StackDefinition(
        "azure-bicep",
        "infrastructure",
        "Azure + Bicep",
        "Azure infrastructure declared through Bicep.",
    ),
    StackDefinition(
        "docker-compose",
        "infrastructure",
        "Docker Compose",
        "Project-local container orchestration for application services and databases.",
        ("configuration",),
        prerequisites=("Docker Compose CLI",),
    ),
    StackDefinition(
        "managed-platform",
        "infrastructure",
        "Managed platform",
        "Infrastructure ownership delegated to a managed application platform.",
    ),
    StackDefinition(
        "github-actions",
        "ci_cd",
        "GitHub Actions",
        "Repository verification workflow executed by GitHub Actions.",
        ("configuration",),
    ),
    StackDefinition(
        "gitlab-ci",
        "ci_cd",
        "GitLab CI",
        "Repository verification pipeline executed by GitLab CI.",
        ("configuration",),
        prerequisites=("GitLab runner with approved stack runtimes",),
    ),
    StackDefinition(
        "ci-cd-not-applicable",
        "ci_cd",
        "Not applicable",
        "No continuous integration service is planned yet.",
    ),
    StackDefinition(
        "github-actions-containers",
        "deployment",
        "GitHub Actions + containers",
        "Container delivery orchestrated with GitHub Actions.",
    ),
    StackDefinition(
        "gitlab-ci-containers",
        "deployment",
        "GitLab CI + containers",
        "Container delivery orchestrated with GitLab CI.",
    ),
    StackDefinition(
        "managed-platform-deployment",
        "deployment",
        "Managed platform deployment",
        "Build and release delegated to a managed platform.",
    ),
    StackDefinition(
        "manual-deployment",
        "deployment",
        "Manual deployment",
        "Owner-operated delivery without an automated pipeline.",
    ),
    StackDefinition(
        "pytest-playwright",
        "testing",
        "pytest + Playwright",
        "Python tests with browser-level Playwright coverage.",
    ),
    StackDefinition(
        "vitest-playwright",
        "testing",
        "Vitest + Playwright",
        "TypeScript unit tests with browser-level Playwright coverage.",
    ),
    StackDefinition(
        "junit-playwright",
        "testing",
        "JUnit + Playwright",
        "JVM tests with browser-level Playwright coverage.",
    ),
    StackDefinition(
        "dotnet-playwright",
        "testing",
        ".NET tests + Playwright",
        ".NET tests with browser-level Playwright coverage.",
    ),
    StackDefinition(
        "go-test-playwright",
        "testing",
        "Go test + Playwright",
        "Go tests with browser-level Playwright coverage.",
    ),
    StackDefinition(
        "flutter-test",
        "testing",
        "Flutter test",
        "Flutter unit and widget tests.",
    ),
    StackDefinition(
        "pytest",
        "testing",
        "pytest",
        "Python unit and integration tests.",
    ),
)


def stacks_for_area(area: str) -> Tuple[StackDefinition, ...]:
    return tuple(stack for stack in STACK_DEFINITIONS if stack.area == area)


def stack_suggestions() -> Dict[str, Tuple[str, ...]]:
    areas = {stack.area for stack in STACK_DEFINITIONS}
    return {
        area: tuple(stack.label for stack in stacks_for_area(area))
        for area in areas
    }


def find_stack(area: str, value: str) -> Optional[StackDefinition]:
    return next(
        (stack for stack in stacks_for_area(area) if stack.matches(value)),
        None,
    )


def automated_stacks(capability: str) -> Iterable[StackDefinition]:
    return (
        stack for stack in STACK_DEFINITIONS if capability in stack.capabilities
    )


def stack_catalog_problems() -> Tuple[str, ...]:
    problems = []
    identifiers = [stack.stack_id for stack in STACK_DEFINITIONS]
    for identifier in sorted(set(identifiers)):
        if identifiers.count(identifier) > 1:
            problems.append(f"duplicate stack ID: {identifier}")
    labels = [
        (stack.area, candidate.casefold())
        for stack in STACK_DEFINITIONS
        for candidate in (stack.label, *stack.aliases)
    ]
    for area, label in sorted(set(labels)):
        if labels.count((area, label)) > 1:
            problems.append(f"duplicate stack label or alias in {area}: {label}")
    for stack in STACK_DEFINITIONS:
        if "scaffold" in stack.capabilities and not stack.adapter_id:
            problems.append(f"scaffold stack has no adapter ID: {stack.stack_id}")
        if "dependencies" in stack.capabilities and "scaffold" not in stack.capabilities:
            problems.append(
                f"dependency automation requires scaffold capability: {stack.stack_id}"
            )
    return tuple(problems)
