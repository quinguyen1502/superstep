from __future__ import annotations

import hashlib
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import yaml

from ..constants import CONFIGURATION_METADATA_PATH, CONFIGURATION_ROOT
from ..project import load_config, load_intake
from ..stacks import find_stack
from .adapters import (
    BUILTIN_CONFIGURATORS,
    ConfigurationContext,
    ConfigurationError,
    StackConfigurator,
    approved_choices,
    matching_configurators,
)
from .models import ConfigurationAction, ConfigurationOutput, ConfigurationPlan


CONFIGURATION_SCHEMA_VERSION = 1
RESERVED_FILES = {
    "AGENTS.md",
    "project-specs.md",
    "project.md",
    "roadmap.md",
    "vision.md",
}
RESERVED_PREFIXES = (".git/", ".factory/", ".factory-state/")


def configuration_source_sha256(context: ConfigurationContext) -> str:
    data = {
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
        "project_name": context.intake.project_name,
        "integration_branch": context.integration_branch,
        "factory_cli_available": context.factory_cli_available,
        "approved_technology": dict(sorted(context.approved.items())),
    }
    rendered = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def create_configuration_plan(
    project_dir: Path,
    configurators: Sequence[StackConfigurator] = BUILTIN_CONFIGURATORS,
) -> ConfigurationPlan:
    if not project_dir.is_dir():
        raise ConfigurationError(f"Project directory does not exist: {project_dir}")
    intake = load_intake(project_dir)
    config = load_config(project_dir)
    context = ConfigurationContext(
        intake,
        approved_choices(intake),
        integration_branch=config.integration_branch,
        factory_cli_available=_factory_cli_available(project_dir),
    )
    matches = matching_configurators(context, configurators)
    plan = ConfigurationPlan(
        project_dir=str(project_dir),
        source_sha256=configuration_source_sha256(context),
        configurators=[configurator.configurator_id for configurator in matches],
    )
    plan.warnings.extend(_configuration_readiness_warnings(context))
    if not matches:
        plan.errors.append(
            "no supported Approved configuration choices are available; approve "
            "Docker Compose with PostgreSQL, MySQL, or MongoDB, and/or GitHub "
            "Actions or GitLab CI"
        )
        return plan

    outputs: Dict[str, ConfigurationOutput] = {}
    for configurator in matches:
        configurator_errors = list(configurator.validate(context))
        plan.errors.extend(configurator_errors)
        plan.warnings.extend(configurator.warnings(context))
        if configurator_errors:
            continue
        try:
            rendered = configurator.render(context)
        except Exception as exc:
            plan.errors.append(
                f"configurator {configurator.configurator_id} failed: {exc}"
            )
            continue
        for output in rendered:
            try:
                _validate_output_path(output.path)
                output.content.decode("utf-8")
            except (ConfigurationError, UnicodeDecodeError) as exc:
                plan.errors.append(
                    f"configurator {configurator.configurator_id} output is invalid: {exc}"
                )
                continue
            if output.configurator_id != configurator.configurator_id:
                plan.errors.append(
                    f"configurator output ID mismatch for {output.path}"
                )
                continue
            if output.path in outputs:
                plan.errors.append(
                    f"configurators generated the same path: {output.path}"
                )
                continue
            outputs[output.path] = output

    plan.actions = _plan_actions(project_dir, list(outputs.values()))
    if not outputs and not plan.errors:
        plan.errors.append("matched stack configurators produced no files")
    return plan


def _configuration_readiness_warnings(
    context: ConfigurationContext,
) -> List[str]:
    warnings: List[str] = []
    backend = context.approved.get("backend")
    database = context.stack_id("database")
    if backend and database in {"postgresql", "mysql", "mongodb"}:
        warnings.append(
            "application database wiring is not generated until the owner approves "
            "a framework driver or ORM and its dependency versions"
        )

    infrastructure = context.stack_id("infrastructure")
    if infrastructure in {"aws-terraform", "gcp-terraform", "azure-bicep"}:
        warnings.append(
            "cloud infrastructure remains specification-only until account/project, "
            "region, runtime target, network, remote state, and credential boundaries "
            "are approved"
        )

    deployment_value = context.approved.get("deployment", "")
    deployment = find_stack("deployment", deployment_value)
    if (
        deployment is not None
        and deployment.stack_id != "manual-deployment"
        and "configuration" not in deployment.capabilities
    ):
        warnings.append(
            f"deployment remains specification-only: {deployment.label}; approve the "
            "runtime target, registry, environment, rollout, rollback, and secret model"
        )
    return warnings


def _plan_actions(
    project_dir: Path,
    outputs: Sequence[ConfigurationOutput],
) -> List[ConfigurationAction]:
    actions: List[ConfigurationAction] = []
    for output in sorted(outputs, key=lambda item: item.path):
        destination = project_dir / output.path
        if destination.is_symlink():
            actions.append(
                ConfigurationAction(
                    output.path, "invalid", "existing path is a symlink", output
                )
            )
        elif not destination.exists():
            actions.append(
                ConfigurationAction(output.path, "create", "path is missing", output)
            )
        elif not destination.is_file():
            actions.append(
                ConfigurationAction(output.path, "invalid", "expected a file", output)
            )
        else:
            existing = destination.read_bytes()
            digest = hashlib.sha256(existing).hexdigest()
            if existing == output.content:
                actions.append(
                    ConfigurationAction(
                        output.path,
                        "keep",
                        "content already matches",
                        output,
                        digest,
                    )
                )
            else:
                actions.append(
                    ConfigurationAction(
                        output.path,
                        "conflict",
                        "existing configuration is preserved until reviewed",
                        output,
                        digest,
                    )
                )
    return actions


def apply_configuration_plan(
    plan: ConfigurationPlan,
    conflict_resolutions: Optional[Mapping[str, ConfigurationOutput]] = None,
) -> List[str]:
    if not plan.ready:
        raise ConfigurationError(
            "Stack configuration plan is not ready; resolve its errors before apply."
        )
    project_dir = Path(plan.project_dir)
    intake = load_intake(project_dir)
    config = load_config(project_dir)
    context = ConfigurationContext(
        intake,
        approved_choices(intake),
        integration_branch=config.integration_branch,
        factory_cli_available=_factory_cli_available(project_dir),
    )
    if configuration_source_sha256(context) != plan.source_sha256:
        raise ConfigurationError(
            "Approved technology changed after planning; create a new stack plan."
        )
    _validate_preconditions(project_dir, plan.actions)
    resolutions = dict(conflict_resolutions or {})
    conflict_paths = {action.path for action in plan.conflicts}
    unknown = sorted(set(resolutions) - conflict_paths)
    if unknown:
        raise ConfigurationError(
            "Configuration resolutions reference unknown conflicts: "
            + ", ".join(unknown)
        )

    publish: Dict[str, Tuple[ConfigurationOutput, str]] = {}
    unresolved: List[str] = []
    for action in plan.actions:
        if action.output is None:
            continue
        if action.status in {"create", "keep"}:
            publish[action.path] = (action.output, "generated")
        elif action.status == "conflict":
            resolution = resolutions.get(action.path)
            if resolution is None:
                unresolved.append(action.path)
            else:
                if (
                    resolution.path != action.path
                    or resolution.configurator_id != action.output.configurator_id
                ):
                    raise ConfigurationError(
                        f"Configuration resolution mismatch: {action.path}"
                    )
                publish[action.path] = (resolution, "reviewed")

    writes: Dict[Path, bytes] = {}
    proposal_root = project_dir / CONFIGURATION_ROOT / "proposals"
    for action in plan.conflicts:
        if action.output is not None:
            writes[proposal_root / action.path] = action.output.content
    for path, (output, _status) in publish.items():
        if next(action for action in plan.actions if action.path == path).status != "keep":
            writes[project_dir / path] = output.content

    metadata = _render_metadata(plan, publish, unresolved)
    writes[project_dir / CONFIGURATION_METADATA_PATH] = metadata.encode("utf-8")
    incomplete = project_dir / CONFIGURATION_ROOT / "INCOMPLETE"
    removals: List[Path] = []
    if unresolved:
        writes[incomplete] = (
            "Stack configuration conflicts require owner review:\n"
            + "".join(f"- {path}\n" for path in unresolved)
        ).encode("utf-8")
    elif incomplete.exists():
        removals.append(incomplete)
    _publish_transaction(writes, removals)
    return unresolved


def _validate_preconditions(
    project_dir: Path,
    actions: Sequence[ConfigurationAction],
) -> None:
    for action in actions:
        destination = project_dir / action.path
        if action.status == "create":
            if destination.exists() or destination.is_symlink():
                raise ConfigurationError(
                    f"Project configuration changed after planning: {action.path}"
                )
            continue
        if action.status not in {"keep", "conflict"}:
            continue
        if destination.is_symlink() or not destination.is_file():
            raise ConfigurationError(
                f"Project configuration changed after planning: {action.path}"
            )
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if digest != action.existing_sha256:
            raise ConfigurationError(
                f"Project configuration changed after planning: {action.path}"
            )


def _publish_transaction(writes: Mapping[Path, bytes], removals: Sequence[Path]) -> None:
    originals: Dict[Path, bytes] = {}
    created: List[Path] = []
    try:
        for destination, content in writes.items():
            if destination.exists():
                if destination.is_symlink() or not destination.is_file():
                    raise ConfigurationError(f"Cannot publish file: {destination}")
                originals[destination] = destination.read_bytes()
            else:
                created.append(destination)
            _atomic_write(destination, content)
        for destination in removals:
            if destination.exists():
                originals[destination] = destination.read_bytes()
                destination.unlink()
    except Exception as exc:
        for path in reversed(created):
            if path.is_file():
                path.unlink()
        for path, content in originals.items():
            _atomic_write(path, content)
        if isinstance(exc, ConfigurationError):
            raise
        raise ConfigurationError(
            f"Stack configuration publish failed and was rolled back: {exc}"
        ) from exc


def _atomic_write(path: Path, content: bytes) -> None:
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "wb", dir=path.parent, delete=False, prefix=f".{path.name}."
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)
    path.chmod(mode)


def _validate_output_path(relative_path: str) -> None:
    path = PurePosixPath(relative_path)
    if (
        not relative_path
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in relative_path
    ):
        raise ConfigurationError(f"Unsafe configuration path: {relative_path}")
    if relative_path in RESERVED_FILES or relative_path == ".git":
        raise ConfigurationError(f"Reserved configuration path: {relative_path}")
    if any(relative_path.startswith(prefix) for prefix in RESERVED_PREFIXES):
        raise ConfigurationError(f"Reserved configuration path: {relative_path}")


def _render_metadata(
    plan: ConfigurationPlan,
    outputs: Mapping[str, Tuple[ConfigurationOutput, str]],
    unresolved: Sequence[str],
) -> str:
    data = {
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
        "status": "incomplete" if unresolved else "applied",
        "source_sha256": plan.source_sha256,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "configurators": list(plan.configurators),
        "outputs": {
            path: {
                "sha256": hashlib.sha256(output.content).hexdigest(),
                "configurator": output.configurator_id,
                "status": status,
            }
            for path, (output, status) in sorted(outputs.items())
        },
        "conflicts": list(unresolved),
    }
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def configuration_problems(
    project_dir: Path,
    *,
    require_state: bool = False,
) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    root = project_dir / CONFIGURATION_ROOT
    metadata_path = project_dir / CONFIGURATION_METADATA_PATH
    incomplete = root / "INCOMPLETE"
    if not root.exists():
        if require_state:
            errors.append("stack configuration has not been applied")
        return errors, warnings
    if incomplete.exists():
        errors.append(
            f"stack configuration is incomplete; review {CONFIGURATION_ROOT}/INCOMPLETE"
        )
    if not metadata_path.is_file():
        errors.append(f"missing stack configuration metadata: {CONFIGURATION_METADATA_PATH}")
        return errors, warnings
    try:
        data = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError("metadata must be a mapping")
        if data.get("schema_version") != CONFIGURATION_SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")
        if data.get("status") not in {"applied", "incomplete"}:
            raise ValueError("status must be applied or incomplete")
        configurators = data.get("configurators")
        if not isinstance(configurators, list) or not all(
            isinstance(item, str) for item in configurators
        ):
            raise ValueError("configurators must be a list of IDs")
        outputs = data.get("outputs", {})
        if not isinstance(outputs, dict):
            raise ValueError("outputs must be a mapping")
        conflicts = data.get("conflicts")
        if not isinstance(conflicts, list) or not all(
            isinstance(item, str) for item in conflicts
        ):
            raise ValueError("conflicts must be a list of paths")
        if data.get("status") == "applied" and conflicts:
            raise ValueError("applied configuration cannot contain conflicts")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(f"invalid stack configuration metadata: {exc}")
        return errors, warnings

    try:
        intake = load_intake(project_dir)
        config = load_config(project_dir)
        context = ConfigurationContext(
            intake,
            approved_choices(intake),
            integration_branch=config.integration_branch,
            factory_cli_available=_factory_cli_available(project_dir),
        )
    except Exception as exc:
        errors.append(f"unable to load stack decisions: {exc}")
        return errors, warnings
    if data.get("source_sha256") != configuration_source_sha256(context):
        warnings.append(
            "Approved technology changed after stack configuration; create a new plan"
        )
    if data.get("status") == "incomplete" and not incomplete.exists():
        errors.append("configuration metadata is incomplete but marker is missing")
    for relative_path, raw_output in outputs.items():
        try:
            _validate_output_path(relative_path)
        except ConfigurationError as exc:
            errors.append(f"invalid managed configuration path: {exc}")
            continue
        if not isinstance(raw_output, dict):
            errors.append(f"invalid configuration output metadata: {relative_path}")
            continue
        if not isinstance(raw_output.get("configurator"), str):
            errors.append(f"invalid configuration adapter metadata: {relative_path}")
        if raw_output.get("status") not in {"generated", "reviewed"}:
            errors.append(f"invalid configuration output status: {relative_path}")
        path = project_dir / relative_path
        if path.is_symlink() or not path.is_file():
            errors.append(f"missing managed configuration output: {relative_path}")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != raw_output.get("sha256"):
            errors.append(f"managed stack configuration drifted: {relative_path}")
    return errors, warnings


def _factory_cli_available(project_dir: Path) -> bool:
    return (
        (project_dir / ".factory" / "pyproject.toml").is_file()
        and (project_dir / ".factory" / "cli" / "factory_cli" / "main.py").is_file()
    )
