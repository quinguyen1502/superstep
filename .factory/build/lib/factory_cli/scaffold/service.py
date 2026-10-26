from __future__ import annotations

import hashlib
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, List, Mapping, Optional, Tuple

import yaml

from ..constants import SCAFFOLD_METADATA_PATH, SCAFFOLD_ROOT
from ..models import ProjectIntake
from ..project import load_intake
from .adapters import ScaffoldRegistry, default_scaffold_registry
from .models import (
    AdapterPreview,
    ScaffoldAction,
    ScaffoldOutput,
    ScaffoldPlan,
    ScaffoldPublishPlan,
    ScaffoldTarget,
)


SCAFFOLD_SCHEMA_VERSION = 1
SCAFFOLD_TARGET_AREAS = {"frontend", "mobile", "backend"}
RESERVED_FILES = {
    "AGENTS.md",
    "project-specs.md",
    "project.md",
    "roadmap.md",
    "vision.md",
}
RESERVED_PREFIXES = (".git/", ".factory/", ".factory-state/")


class ScaffoldError(Exception):
    """Blocking scaffold planning, staging, or publication problem."""


def approved_targets(intake: ProjectIntake) -> List[ScaffoldTarget]:
    return [
        ScaffoldTarget(area=area, technology=choice.value.strip())
        for area, choice in intake.tech_stack.items()
        if choice.status == "Approved" and choice.value.strip()
    ]


def scaffold_source_sha256(intake: ProjectIntake) -> str:
    source = {
        "schema_version": SCAFFOLD_SCHEMA_VERSION,
        "project_name": intake.project_name,
        "approved_technology": [
            {"area": target.area, "technology": target.technology}
            for target in approved_targets(intake)
        ],
    }
    rendered = yaml.safe_dump(source, sort_keys=False, allow_unicode=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def create_scaffold_plan(
    project_dir: Path,
    registry: Optional[ScaffoldRegistry] = None,
) -> ScaffoldPlan:
    if not project_dir.is_dir():
        raise ScaffoldError(f"Project directory does not exist: {project_dir}")
    intake = load_intake(project_dir)
    approved = approved_targets(intake)
    targets = [target for target in approved if target.area in SCAFFOLD_TARGET_AREAS]
    context_targets = [
        target for target in approved if target.area not in SCAFFOLD_TARGET_AREAS
    ]
    plan = ScaffoldPlan(
        project_dir=str(project_dir),
        source_sha256=scaffold_source_sha256(intake),
        targets=targets,
        context_targets=context_targets,
    )
    if not targets:
        plan.errors.append(
            "no Approved frontend, mobile, or backend choice is available; "
            "approve a source stack before scaffolding"
        )
        return plan

    for target in context_targets:
        plan.warnings.append(
            f"context decision is not independently scaffolded: {target.label}"
        )

    registry = registry or default_scaffold_registry()
    assignments: Dict[str, List[ScaffoldTarget]] = {}
    for target in targets:
        try:
            matches = registry.matching(target)
        except Exception as exc:
            plan.errors.append(
                f"adapter matching failed for {target.label}: {exc}"
            )
            continue
        if not matches:
            plan.errors.append(f"unsupported scaffold target: {target.label}")
            continue
        if len(matches) > 1:
            identifiers = ", ".join(adapter.adapter_id for adapter in matches)
            plan.errors.append(
                f"ambiguous scaffold target {target.label}; matching adapters: {identifiers}"
            )
            continue
        assignments.setdefault(matches[0].adapter_id, []).append(target)

    for adapter in registry.adapters:
        targets_for_adapter = assignments.get(adapter.adapter_id)
        if not targets_for_adapter:
            continue
        try:
            preview = adapter.preview(targets_for_adapter)
        except Exception as exc:
            plan.errors.append(f"adapter {adapter.adapter_id} preview failed: {exc}")
            continue
        if not isinstance(preview, AdapterPreview):
            plan.errors.append(
                f"adapter {adapter.adapter_id} preview returned an invalid result"
            )
            continue
        if preview.adapter_id != adapter.adapter_id:
            plan.errors.append(
                f"adapter preview ID mismatch: expected {adapter.adapter_id}, "
                f"received {preview.adapter_id}"
            )
            continue
        if preview.adapter_version != adapter.adapter_version:
            plan.errors.append(
                f"adapter preview version mismatch for {adapter.adapter_id}: "
                f"expected {adapter.adapter_version}, received {preview.adapter_version}"
            )
            continue
        try:
            for expected_path in preview.expected_paths:
                _validate_relative_path(expected_path)
        except ScaffoldError as exc:
            plan.errors.append(f"adapter {adapter.adapter_id} preview is invalid: {exc}")
            continue
        normalized_preview = AdapterPreview(
            adapter_id=preview.adapter_id,
            adapter_version=preview.adapter_version,
            targets=list(targets_for_adapter),
            available=preview.available,
            command=list(preview.command),
            expected_paths=list(preview.expected_paths),
            reason=preview.reason,
        )
        plan.adapters.append(normalized_preview)
        if not normalized_preview.available:
            plan.errors.append(
                f"adapter {adapter.adapter_id} is unavailable: "
                f"{normalized_preview.reason or 'required executable was not detected'}"
            )
    return plan


def stage_scaffold(
    plan: ScaffoldPlan,
    registry: Optional[ScaffoldRegistry] = None,
) -> ScaffoldPublishPlan:
    if not plan.ready:
        raise ScaffoldError("Scaffold plan is not ready; resolve its errors before apply.")
    project_dir = Path(plan.project_dir)
    intake = load_intake(project_dir)
    if scaffold_source_sha256(intake) != plan.source_sha256:
        raise ScaffoldError("Approved technology changed after planning; create a new plan.")
    registry = registry or default_scaffold_registry()
    outputs: Dict[str, ScaffoldOutput] = {}

    with tempfile.TemporaryDirectory(prefix="factory-scaffold-") as temporary:
        staging_root = Path(temporary)
        for preview in plan.adapters:
            try:
                adapter = registry.get(preview.adapter_id)
            except KeyError as exc:
                raise ScaffoldError(
                    f"Scaffold adapter disappeared after planning: {preview.adapter_id}"
                ) from exc
            if adapter.adapter_version != preview.adapter_version:
                raise ScaffoldError(
                    f"Scaffold adapter changed after planning: {preview.adapter_id}"
                )
            adapter_root = staging_root / preview.adapter_id
            adapter_root.mkdir(parents=True)
            try:
                adapter.execute(preview.targets, adapter_root)
            except Exception as exc:
                raise ScaffoldError(
                    f"Adapter {preview.adapter_id} failed in staging: {exc}"
                ) from exc
            findings = adapter.validate(preview.targets, adapter_root)
            if findings:
                raise ScaffoldError(
                    f"Adapter {preview.adapter_id} validation failed: "
                    + "; ".join(findings)
                )
            for expected_path in preview.expected_paths:
                if not (adapter_root / expected_path).exists():
                    raise ScaffoldError(
                        f"Adapter {preview.adapter_id} did not create expected path: "
                        f"{expected_path}"
                    )
            for output in _collect_outputs(adapter_root, preview.adapter_id):
                if output.path in outputs:
                    raise ScaffoldError(
                        f"Scaffold adapters generated the same path: {output.path}"
                    )
                outputs[output.path] = output

    if not outputs:
        raise ScaffoldError("Scaffold adapters produced no files.")
    return _build_publish_plan(plan, list(outputs.values()))


def _collect_outputs(staging_root: Path, adapter_id: str) -> List[ScaffoldOutput]:
    outputs: List[ScaffoldOutput] = []
    for path in sorted(staging_root.rglob("*")):
        if path.is_symlink():
            raise ScaffoldError(
                f"Adapter {adapter_id} generated an unsupported symlink: "
                f"{path.relative_to(staging_root)}"
            )
        if path.is_dir():
            continue
        if not path.is_file():
            raise ScaffoldError(
                f"Adapter {adapter_id} generated an unsupported file type: "
                f"{path.relative_to(staging_root)}"
            )
        relative_path = path.relative_to(staging_root).as_posix()
        _validate_output_path(relative_path)
        mode = path.stat().st_mode
        outputs.append(
            ScaffoldOutput(
                path=relative_path,
                content=path.read_bytes(),
                adapter_id=adapter_id,
                executable=bool(mode & stat.S_IXUSR),
            )
        )
    return outputs


def _validate_relative_path(relative_path: str) -> None:
    path = PurePosixPath(relative_path)
    if not relative_path or path.is_absolute() or ".." in path.parts:
        raise ScaffoldError(f"Unsafe scaffold path: {relative_path}")
    if "\\" in relative_path:
        raise ScaffoldError(f"Scaffold paths must use forward slashes: {relative_path}")


def _validate_output_path(relative_path: str) -> None:
    _validate_relative_path(relative_path)
    if relative_path in RESERVED_FILES or relative_path == ".git":
        raise ScaffoldError(f"Adapter attempted to generate a reserved path: {relative_path}")
    if any(relative_path.startswith(prefix) for prefix in RESERVED_PREFIXES):
        raise ScaffoldError(f"Adapter attempted to generate a reserved path: {relative_path}")


def _build_publish_plan(
    scaffold_plan: ScaffoldPlan,
    outputs: List[ScaffoldOutput],
) -> ScaffoldPublishPlan:
    project_dir = Path(scaffold_plan.project_dir)
    actions: List[ScaffoldAction] = []
    for output in sorted(outputs, key=lambda item: item.path):
        destination = project_dir / output.path
        if destination.is_symlink():
            actions.append(
                ScaffoldAction(output.path, "invalid", "existing path is a symlink", output)
            )
        elif not destination.exists():
            actions.append(
                ScaffoldAction(output.path, "create", "path is missing", output)
            )
        elif not destination.is_file():
            actions.append(
                ScaffoldAction(output.path, "invalid", "expected a file", output)
            )
        else:
            existing_content = destination.read_bytes()
            existing_sha256 = hashlib.sha256(existing_content).hexdigest()
            existing_executable = _is_executable(destination)
            same_content = existing_content == output.content
            same_mode = existing_executable == output.executable
            if same_content and same_mode:
                actions.append(
                    ScaffoldAction(
                        output.path,
                        "keep",
                        "content already matches",
                        output,
                        existing_sha256,
                        existing_executable,
                    )
                )
            else:
                actions.append(
                    ScaffoldAction(
                        output.path,
                        "conflict",
                        "existing source is preserved until reviewed",
                        output,
                        existing_sha256,
                        existing_executable,
                    )
                )
    return ScaffoldPublishPlan(
        project_dir=scaffold_plan.project_dir,
        source_sha256=scaffold_plan.source_sha256,
        adapters=list(scaffold_plan.adapters),
        actions=actions,
    )


def apply_scaffold_plan(
    plan: ScaffoldPublishPlan,
    conflict_resolutions: Optional[Mapping[str, ScaffoldOutput]] = None,
) -> List[str]:
    if plan.invalid:
        raise ScaffoldError("Scaffold publish plan contains invalid paths.")
    project_dir = Path(plan.project_dir)
    intake = load_intake(project_dir)
    if scaffold_source_sha256(intake) != plan.source_sha256:
        raise ScaffoldError("Approved technology changed after staging; scaffold again.")
    _validate_publish_preconditions(project_dir, plan.actions)
    resolutions = dict(conflict_resolutions or {})
    conflict_paths = {action.path for action in plan.conflicts}
    unknown = sorted(set(resolutions) - conflict_paths)
    if unknown:
        raise ScaffoldError(
            "Scaffold resolutions reference unknown conflicts: " + ", ".join(unknown)
        )
    for path, output in resolutions.items():
        if output.path != path:
            raise ScaffoldError(f"Scaffold resolution path mismatch: {path}")
        original = next(
            action.output for action in plan.conflicts if action.path == path
        )
        if original is None or output.adapter_id != original.adapter_id:
            raise ScaffoldError(f"Scaffold resolution adapter mismatch: {path}")

    proposal_root = project_dir / SCAFFOLD_ROOT / "proposals"
    for action in plan.conflicts:
        if action.output is not None:
            _atomic_write_bytes(proposal_root / action.path, action.output.content)

    publish_outputs: Dict[str, Tuple[ScaffoldOutput, str]] = {}
    unresolved: List[str] = []
    for action in plan.actions:
        if action.output is None:
            continue
        if action.status in {"create", "keep"}:
            publish_outputs[action.path] = (action.output, "generated")
        elif action.status == "conflict":
            resolution = resolutions.get(action.path)
            if resolution is None:
                unresolved.append(action.path)
            else:
                publish_outputs[action.path] = (resolution, "reviewed")

    metadata = _render_metadata(plan, publish_outputs, unresolved)
    incomplete = project_dir / SCAFFOLD_ROOT / "INCOMPLETE"
    state_writes = {
        project_dir / SCAFFOLD_METADATA_PATH: metadata.encode("utf-8"),
    }
    state_removals: List[Path] = []
    if unresolved:
        state_writes[incomplete] = (
            "Scaffold conflicts require owner review:\n"
            + "".join(f"- {path}\n" for path in unresolved)
        ).encode("utf-8")
    elif incomplete.exists():
        state_removals.append(incomplete)
    _publish_transaction(
        project_dir,
        plan.actions,
        publish_outputs,
        state_writes,
        state_removals,
    )
    return unresolved


def _validate_publish_preconditions(
    project_dir: Path,
    actions: List[ScaffoldAction],
) -> None:
    for action in actions:
        destination = project_dir / action.path
        if action.status == "create":
            if destination.exists() or destination.is_symlink():
                raise ScaffoldError(
                    f"Project source changed after staging: {action.path}"
                )
            continue
        if action.status not in {"keep", "conflict"}:
            continue
        if destination.is_symlink() or not destination.is_file():
            raise ScaffoldError(
                f"Project source changed after staging: {action.path}"
            )
        actual_sha256 = hashlib.sha256(destination.read_bytes()).hexdigest()
        if (
            actual_sha256 != action.existing_sha256
            or _is_executable(destination) != action.existing_executable
        ):
            raise ScaffoldError(
                f"Project source changed after staging: {action.path}"
            )


def _publish_transaction(
    project_dir: Path,
    actions: List[ScaffoldAction],
    outputs: Mapping[str, Tuple[ScaffoldOutput, str]],
    state_writes: Mapping[Path, bytes],
    state_removals: List[Path],
) -> None:
    action_status = {action.path: action.status for action in actions}
    created: List[Path] = []
    originals: Dict[Path, Tuple[bytes, int]] = {}
    try:
        for relative_path, (output, _status) in outputs.items():
            destination = project_dir / relative_path
            status = action_status[relative_path]
            if status == "keep":
                continue
            if destination.exists():
                originals[destination] = (
                    destination.read_bytes(),
                    stat.S_IMODE(destination.stat().st_mode),
                )
            else:
                created.append(destination)
            _atomic_write_bytes(destination, output.content)
            _set_executable(destination, output.executable)
        for destination, content in state_writes.items():
            if destination.exists():
                originals[destination] = (
                    destination.read_bytes(),
                    stat.S_IMODE(destination.stat().st_mode),
                )
            else:
                created.append(destination)
            _atomic_write_bytes(destination, content)
        for destination in state_removals:
            if not destination.exists():
                continue
            originals[destination] = (
                destination.read_bytes(),
                stat.S_IMODE(destination.stat().st_mode),
            )
            destination.unlink()
    except Exception as exc:
        for path in reversed(created):
            if path.exists() and path.is_file():
                path.unlink()
        for path, (content, mode) in originals.items():
            _atomic_write_bytes(path, content)
            path.chmod(mode)
        raise ScaffoldError(f"Scaffold publish failed and was rolled back: {exc}") from exc


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "wb", dir=path.parent, delete=False, prefix=f".{path.name}."
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def _set_executable(path: Path, executable: bool) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if executable:
        path.chmod(mode | stat.S_IXUSR)
    else:
        path.chmod(mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)


def _is_executable(path: Path) -> bool:
    return bool(path.stat().st_mode & stat.S_IXUSR)


def _render_metadata(
    plan: ScaffoldPublishPlan,
    outputs: Mapping[str, Tuple[ScaffoldOutput, str]],
    unresolved: List[str],
) -> str:
    data = {
        "schema_version": SCAFFOLD_SCHEMA_VERSION,
        "status": "incomplete" if unresolved else "applied",
        "source_sha256": plan.source_sha256,
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "adapters": [
            {"id": adapter.adapter_id, "version": adapter.adapter_version}
            for adapter in plan.adapters
        ],
        "outputs": {
            path: {
                "sha256": hashlib.sha256(output.content).hexdigest(),
                "executable": output.executable,
                "adapter": output.adapter_id,
                "status": status,
            }
            for path, (output, status) in sorted(outputs.items())
        },
        "conflicts": list(unresolved),
    }
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def scaffold_problems(project_dir: Path) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    root = project_dir / SCAFFOLD_ROOT
    metadata_path = project_dir / SCAFFOLD_METADATA_PATH
    incomplete = root / "INCOMPLETE"
    if not root.exists():
        return errors, warnings
    if incomplete.exists():
        errors.append(
            f"scaffolding is incomplete; review {SCAFFOLD_ROOT}/INCOMPLETE and proposals"
        )
    if not metadata_path.is_file():
        errors.append(f"missing scaffold metadata: {SCAFFOLD_METADATA_PATH}")
        return errors, warnings
    try:
        data = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError("metadata must be a mapping")
        if data.get("schema_version") != SCAFFOLD_SCHEMA_VERSION:
            raise ValueError("unsupported schema_version")
        outputs = data.get("outputs", {})
        if not isinstance(outputs, dict):
            raise ValueError("outputs must be a mapping")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(f"invalid scaffold metadata: {exc}")
        return errors, warnings

    try:
        intake = load_intake(project_dir)
    except Exception as exc:
        errors.append(f"unable to load project intake for scaffold validation: {exc}")
        return errors, warnings
    if data.get("source_sha256") != scaffold_source_sha256(intake):
        warnings.append(
            "Approved technology changed after scaffolding; create and review a new plan"
        )
    if data.get("status") == "incomplete" and not incomplete.exists():
        errors.append("scaffold metadata is incomplete but INCOMPLETE marker is missing")

    for relative_path, raw_output in outputs.items():
        try:
            _validate_output_path(relative_path)
        except ScaffoldError as exc:
            errors.append(f"invalid managed scaffold path: {exc}")
            continue
        if not isinstance(raw_output, dict):
            errors.append(f"invalid scaffold output metadata: {relative_path}")
            continue
        path = project_dir / relative_path
        if path.is_symlink() or not path.is_file():
            errors.append(f"missing managed scaffold output: {relative_path}")
            continue
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if raw_output.get("sha256") != actual_hash:
            errors.append(f"managed scaffold output drifted: {relative_path}")
        expected_executable = raw_output.get("executable")
        if not isinstance(expected_executable, bool):
            errors.append(f"invalid executable metadata: {relative_path}")
        elif expected_executable != _is_executable(path):
            errors.append(f"managed scaffold executable bit drifted: {relative_path}")
    return errors, warnings
