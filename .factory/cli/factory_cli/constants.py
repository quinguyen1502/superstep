from __future__ import annotations


FRAMEWORK_ASSETS = (
    "AGENTS.md",
    "agents",
    "workflows",
    "templates",
    "docs",
    "bin",
    "cli",
    "pyproject.toml",
)
TASK_STATES = ("backlog", "todo", "doing", "review", "qa", "done")
TOOL_IDS = ("codex", "cursor", "claude-code", "grok")
TOOL_KIT_LEVELS = ("instructions", "guardrails", "automation", "custom")
STACK_STATUSES = ("Approved", "Preferred", "Proposed", "Unknown")
PROJECT_PRESET_IDS = ("web-app", "api", "cli", "mobile")
SOURCE_STACK_AREAS = ("frontend", "mobile", "backend")
REFINEMENT_SECTION_IDS = (
    "all",
    "overview",
    "scope",
    "experience",
    "technical",
    "quality",
    "risk-validation",
)

FACTORY_STATE_DIR = ".factory-state"
TASK_ROOT = f"{FACTORY_STATE_DIR}/tasks"
STANDARDS_ROOT = f"{FACTORY_STATE_DIR}/standards"
DECISIONS_ROOT = f"{FACTORY_STATE_DIR}/decisions"
ARTIFACTS_ROOT = f"{FACTORY_STATE_DIR}/artifacts"
INTAKE_ROOT = f"{FACTORY_STATE_DIR}/intake"
FACTORY_CONFIG_PATH = f"{FACTORY_STATE_DIR}/factory.yaml"
TOOLING_ROOT = f"{FACTORY_STATE_DIR}/tooling"
TOOL_POLICY_PATH = f"{TOOLING_ROOT}/tool-policy.yaml"
TOOL_GENERATED_PATH = f"{TOOLING_ROOT}/generated.yaml"
SKILLS_GENERATED_PATH = f"{FACTORY_STATE_DIR}/skills/generated.yaml"
SCAFFOLD_ROOT = f"{FACTORY_STATE_DIR}/scaffolding"
SCAFFOLD_METADATA_PATH = f"{SCAFFOLD_ROOT}/generated.yaml"
DEPENDENCY_ROOT = f"{FACTORY_STATE_DIR}/dependencies"
DEPENDENCY_METADATA_PATH = f"{DEPENDENCY_ROOT}/installed.yaml"
VERIFICATION_ROOT = f"{FACTORY_STATE_DIR}/verification"
VERIFICATION_METADATA_PATH = f"{VERIFICATION_ROOT}/latest.yaml"
VERIFICATION_RUNS_ROOT = f"{VERIFICATION_ROOT}/runs"
VERIFICATION_KINDS = (
    "check",
    "test",
    "lint",
    "typecheck",
    "build",
    "format",
    "analyze",
)
VERIFICATION_QUICK_KINDS = (
    "check",
    "test",
    "lint",
    "typecheck",
    "format",
    "analyze",
)
ARCHIVE_ROOT = f"{FACTORY_STATE_DIR}/archive"
ARCHIVE_TASK_ROOT = f"{ARCHIVE_ROOT}/tasks"
ARCHIVE_ARTIFACT_ROOT = f"{ARCHIVE_ROOT}/artifacts"
GC_DEFAULT_KEEP = 20
GC_COMPANION_TYPES = ("REV", "QA", "SUM")

STANDARD_AREAS = (
    "architecture",
    "coding",
    "delivery",
    "documentation",
    "operations",
    "review",
    "security",
    "testing",
)

REQUIRED_PROJECT_PATHS = (
    "AGENTS.md",
    "project-specs.md",
    "vision.md",
    "project.md",
    "roadmap.md",
    ".factory/AGENTS.md",
    ".factory/agents",
    ".factory/workflows",
    ".factory/templates",
    ".factory/docs",
    FACTORY_STATE_DIR,
    FACTORY_CONFIG_PATH,
    STANDARDS_ROOT,
    DECISIONS_ROOT,
    TASK_ROOT,
    ARTIFACTS_ROOT,
    INTAKE_ROOT,
    TOOL_POLICY_PATH,
)
