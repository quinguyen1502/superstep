from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .constants import (
    TOOL_GENERATED_PATH,
    TOOL_IDS,
    TOOL_KIT_LEVELS,
    TOOL_POLICY_PATH,
    TOOLING_ROOT,
)
from .models import ImportAction, ImportPlan


ADAPTER_VERSION = 1
ACTIVE_LEVELS = {"guardrails", "automation", "custom"}


@dataclass
class CommandPolicy:
    command: str = ""
    evidence: str = "Expected"

    def validate(self) -> None:
        if not isinstance(self.command, str):
            raise ValueError("Tool policy commands must be strings.")
        if self.evidence not in {"Expected", "Observed"}:
            raise ValueError("Command evidence must be Expected or Observed.")


@dataclass
class ToolPolicy:
    schema_version: int = 1
    status: str = "proposed"
    level: str = "instructions"
    enabled_tools: List[str] = field(default_factory=lambda: list(TOOL_IDS))
    protect_factory_assets: bool = False
    validate_on_stop: bool = False
    commands: Dict[str, CommandPolicy] = field(default_factory=dict)

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f"Unsupported tool policy schema: {self.schema_version}")
        if self.status not in {"proposed", "approved"}:
            raise ValueError("Tool policy status must be proposed or approved.")
        if self.level not in TOOL_KIT_LEVELS:
            raise ValueError(f"Unsupported tool kit level: {self.level}")
        if not isinstance(self.enabled_tools, list):
            raise ValueError("Tool policy enabled_tools must be a list.")
        invalid = sorted(set(self.enabled_tools) - set(TOOL_IDS))
        if invalid:
            raise ValueError(f"Unsupported AI tools: {', '.join(invalid)}")
        if not all(isinstance(value, bool) for value in (
            self.protect_factory_assets,
            self.validate_on_stop,
        )):
            raise ValueError("Tool policy hook flags must be booleans.")
        if not isinstance(self.commands, dict):
            raise ValueError("Tool policy commands must be a mapping.")
        for command in self.commands.values():
            if not isinstance(command, CommandPolicy):
                raise ValueError("Tool policy command entries must be mappings.")
            command.validate()

    @property
    def active(self) -> bool:
        return self.status == "approved" and self.level in ACTIVE_LEVELS

    def to_yaml(self) -> str:
        self.validate()
        return yaml.safe_dump(
            asdict(self), sort_keys=False, allow_unicode=True, default_flow_style=False
        )

    @classmethod
    def from_yaml(cls, content: str) -> "ToolPolicy":
        try:
            data = yaml.safe_load(content) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid tool policy YAML: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Tool policy must be a YAML mapping.")
        raw_commands = data.pop("commands", {}) or {}
        if not isinstance(raw_commands, dict):
            raise ValueError("Tool policy commands must be a mapping.")
        try:
            policy = cls(**data)
            policy.commands = {
                name: CommandPolicy(**value)
                for name, value in raw_commands.items()
            }
        except (TypeError, AttributeError) as exc:
            raise ValueError(f"Invalid tool policy fields: {exc}") from exc
        policy.validate()
        return policy


def parse_command_spec(spec: str) -> Tuple[str, str]:
    """Parse a ``NAME=COMMAND`` overlay from ``factory tools configure``."""
    if "=" not in spec:
        raise ValueError("Command spec must be NAME=COMMAND.")
    name, command = spec.split("=", 1)
    name = name.strip()
    command = command.strip()
    if not name or not command:
        raise ValueError("Command spec must be NAME=COMMAND.")
    return name, command


def overlay_tool_policy(
    policy: ToolPolicy,
    *,
    level: Optional[str] = None,
    status: Optional[str] = None,
    enabled_tools: Optional[List[str]] = None,
    protect_factory_assets: Optional[bool] = None,
    validate_on_stop: Optional[bool] = None,
    commands: Optional[Dict[str, str]] = None,
) -> ToolPolicy:
    """Return a copy of ``policy`` with explicit configure flags applied.

    Passing ``level`` without ``status`` or hook flags follows
    ``default_tool_policy``: active levels are approved with hooks on,
    ``instructions`` is proposed with hooks off. Explicit flags win.
    Named commands merge into the existing map and keep prior evidence.
    """
    updated = ToolPolicy(
        schema_version=policy.schema_version,
        status=policy.status,
        level=policy.level,
        enabled_tools=list(policy.enabled_tools),
        protect_factory_assets=policy.protect_factory_assets,
        validate_on_stop=policy.validate_on_stop,
        commands=dict(policy.commands),
    )
    if level is not None:
        updated.level = level
        active = level in ACTIVE_LEVELS
        if status is None:
            updated.status = "approved" if active else "proposed"
        if protect_factory_assets is None:
            updated.protect_factory_assets = active
        if validate_on_stop is None:
            updated.validate_on_stop = active
    if status is not None:
        updated.status = status
    if enabled_tools is not None:
        updated.enabled_tools = list(dict.fromkeys(enabled_tools))
    if protect_factory_assets is not None:
        updated.protect_factory_assets = protect_factory_assets
    if validate_on_stop is not None:
        updated.validate_on_stop = validate_on_stop
    if commands:
        for name, command in commands.items():
            evidence = (
                updated.commands[name].evidence
                if name in updated.commands
                else "Expected"
            )
            updated.commands[name] = CommandPolicy(command=command, evidence=evidence)
    updated.validate()
    return updated


def default_tool_policy(
    enabled_tools: List[str],
    level: str = "instructions",
    commands: Optional[Dict[str, str]] = None,
) -> ToolPolicy:
    active = level in ACTIVE_LEVELS
    policy = ToolPolicy(
        status="approved" if active else "proposed",
        level=level,
        enabled_tools=list(dict.fromkeys(enabled_tools)),
        protect_factory_assets=active,
        validate_on_stop=active,
        commands={
            name: CommandPolicy(command=value, evidence="Expected")
            for name, value in (commands or {}).items()
            if value.strip()
        },
    )
    policy.validate()
    return policy


def load_tool_policy(project_dir: Path) -> ToolPolicy:
    path = project_dir / TOOL_POLICY_PATH
    if not path.is_file():
        raise ValueError(f"Missing tool policy: {TOOL_POLICY_PATH}")
    return ToolPolicy.from_yaml(path.read_text(encoding="utf-8"))


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _configuration_problem(relative_path: str, content: str) -> Optional[str]:
    if relative_path == ".codex/config.toml":
        try:
            import tomllib
        except ImportError:  # pragma: no cover - Python 3.9/3.10 fallback
            required = (
                'approval_policy = "on-request"',
                'sandbox_mode = "workspace-write"',
                "[permissions.factory-project]",
            )
            if not all(item in content for item in required):
                return "missing required Codex guardrail settings"
        else:
            try:
                parsed = tomllib.loads(content)
            except tomllib.TOMLDecodeError as exc:
                return str(exc)
            if not isinstance(parsed.get("permissions"), dict):
                return "permissions must be a TOML table"
        return None
    if not relative_path.endswith(".json"):
        return None
    try:
        parsed_json = json.loads(content)
    except json.JSONDecodeError as exc:
        return str(exc)
    if not isinstance(parsed_json, dict):
        return "root must be an object"
    if relative_path == ".codex/hooks.json" and not isinstance(
        parsed_json.get("hooks"), dict
    ):
        return "hooks must be an object"
    if relative_path == ".claude/settings.json" and (
        not isinstance(parsed_json.get("permissions"), dict)
        or not isinstance(parsed_json.get("hooks"), dict)
    ):
        return "permissions and hooks must be objects"
    return None


def render_codex_config() -> str:
    return """# Generated from .factory-state/tooling/tool-policy.yaml.
# Review changes through `factory tools configure`; local authentication stays user-owned.
approval_policy = "on-request"
sandbox_mode = "workspace-write"
default_permissions = "factory-project"

[permissions.factory-project]
description = "Workspace edits with factory policy and sensitive files protected."
extends = ":workspace"

[permissions.factory-project.filesystem.":workspace_roots"]
".factory" = "read"
".factory-state/tooling" = "read"
".env" = "deny"
".env.*" = "deny"
"**/*.env" = "deny"
"secrets" = "deny"
"secrets/**" = "deny"
"""


def _hook_command(path: str, claude: bool = False) -> str:
    if claude:
        return f'python3 "${{CLAUDE_PROJECT_DIR}}/{path}"'
    return f'python3 "$(git rev-parse --show-toplevel)/{path}"'


def render_codex_hooks(policy: ToolPolicy) -> str:
    hooks: Dict[str, List[Dict[str, Any]]] = {}
    if policy.protect_factory_assets:
        hooks["PreToolUse"] = [{
            "matcher": "Bash|apply_patch|Edit|Write",
            "hooks": [{
                "type": "command",
                "command": _hook_command(f"{TOOLING_ROOT}/hooks/pre_tool_guard.py"),
                "timeout": 10,
                "statusMessage": "Checking factory guardrails",
            }],
        }]
    if policy.validate_on_stop:
        hooks["Stop"] = [{
            "hooks": [{
                "type": "command",
                "command": _hook_command(f"{TOOLING_ROOT}/hooks/stop_validate.py"),
                "timeout": 300,
                "statusMessage": "Validating factory artifacts",
            }],
        }]
    return json.dumps({"hooks": hooks}, indent=2, ensure_ascii=False) + "\n"


def render_claude_settings(policy: ToolPolicy) -> str:
    settings: Dict[str, Any] = {
        "$schema": "https://json.schemastore.org/claude-code-settings.json",
        "permissions": {
            "allow": [],
            "ask": [
                "Bash(git push *)",
                "Bash(git tag *)",
                "Bash(gh pr merge *)",
            ],
            "deny": [
                "Read(./.env)",
                "Read(./.env.*)",
                "Read(./secrets/**)",
                "Edit(./.factory/**)",
                "Edit(./.factory-state/tooling/**)",
            ],
        },
        "hooks": {},
    }
    if policy.protect_factory_assets:
        settings["hooks"]["PreToolUse"] = [{
            "matcher": "Bash|Write|Edit|MultiEdit",
            "hooks": [{
                "type": "command",
                "command": _hook_command(
                    f"{TOOLING_ROOT}/hooks/pre_tool_guard.py", claude=True
                ),
                "timeout": 10,
            }],
        }]
    if policy.validate_on_stop:
        settings["hooks"]["Stop"] = [{
            "hooks": [{
                "type": "command",
                "command": _hook_command(
                    f"{TOOLING_ROOT}/hooks/stop_validate.py", claude=True
                ),
                "timeout": 300,
            }],
        }]
    return json.dumps(settings, indent=2, ensure_ascii=False) + "\n"


PRE_TOOL_GUARD = r'''#!/usr/bin/env python3
"""Block obvious writes to owner-controlled factory configuration."""
import json
import re
import sys

payload = json.load(sys.stdin)
tool_name = str(payload.get("tool_name") or payload.get("toolName") or "")
tool_input = payload.get("tool_input") or payload.get("toolInput") or payload.get("input") or {}
serialized = json.dumps(tool_input, ensure_ascii=False)
command = (
    str(tool_input.get("command") or tool_input.get("cmd") or "")
    if isinstance(tool_input, dict)
    else ""
)
protected = re.compile(
    r"(?<![\w-])(?:\.factory(?:/|(?=[\"'\s]|$))|"
    r"\.factory-state/tooling(?:/|(?=[\"'\s]|$)))"
)
path_write = bool(protected.search(serialized)) and tool_name.lower() in {
    "write", "edit", "multiedit", "apply_patch"
}
destructive = bool(
    protected.search(command)
    and re.search(
        r"(?:rm\s+(?:-[^ ]*r[^ ]*f|-[^ ]*f[^ ]*r)|git\s+(?:clean|reset\s+--hard)|(?:>|tee\s+))",
        command,
    )
)
if path_write or destructive:
    print("Factory guardrail blocked a write to owner-controlled factory assets.", file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(0)
'''


STOP_VALIDATE_TEMPLATE = r'''#!/usr/bin/env python3
"""Run report-only factory validation when an agent turn stops."""
import json
import os
import subprocess
import sys
from pathlib import Path

root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
commands = [["factory", "validate", str(root)]]
commands.extend(json.loads(__OBSERVED_COMMANDS__))
for command in commands:
    try:
        result = subprocess.run(
            command if isinstance(command, list) else command,
            cwd=root,
            shell=isinstance(command, str),
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        if output:
            print(output, file=sys.stderr)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Factory validation hook warning: {exc}", file=sys.stderr)
# Report-only: validation findings must not trap the agent in a Stop hook loop.
print("{}")
raise SystemExit(0)
'''


def render_stop_validate(policy: ToolPolicy) -> str:
    safe_names = {"test", "lint", "typecheck", "build", "format"}
    observed = (
        [
            command.command
            for name, command in policy.commands.items()
            if name in safe_names
            and command.command
            and command.evidence == "Observed"
        ]
        if policy.level == "automation"
        else []
    )
    encoded = json.dumps(json.dumps(observed))
    return STOP_VALIDATE_TEMPLATE.replace("__OBSERVED_COMMANDS__", encoded)


def render_managed_assets(policy: ToolPolicy) -> Dict[str, str]:
    policy.validate()
    assets = {
        f"{TOOLING_ROOT}/hooks/pre_tool_guard.py": PRE_TOOL_GUARD,
        f"{TOOLING_ROOT}/hooks/stop_validate.py": render_stop_validate(policy),
    }
    if policy.active and "codex" in policy.enabled_tools:
        assets[".codex/config.toml"] = render_codex_config()
        assets[".codex/hooks.json"] = render_codex_hooks(policy)
    if policy.active and "claude-code" in policy.enabled_tools:
        assets[".claude/settings.json"] = render_claude_settings(policy)
    return assets


def render_generated_metadata(policy: ToolPolicy, assets: Dict[str, str]) -> str:
    data = {
        "schema_version": 1,
        "policy_sha256": _sha256(policy.to_yaml()),
        "adapters": {
            tool: {"version": ADAPTER_VERSION}
            for tool in policy.enabled_tools
        },
        "outputs": {
            path: _sha256(content)
            for path, content in sorted(assets.items())
        },
    }
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def render_tooling_bundle(policy: ToolPolicy) -> Dict[str, str]:
    assets = render_managed_assets(policy)
    return {
        TOOL_POLICY_PATH: policy.to_yaml(),
        **assets,
        TOOL_GENERATED_PATH: render_generated_metadata(policy, assets),
    }


def plan_tooling(project_dir: Path, policy: ToolPolicy) -> ImportPlan:
    actions: List[ImportAction] = []
    expected = render_managed_assets(policy)
    for relative_path, content in expected.items():
        path = project_dir / relative_path
        if not path.exists():
            actions.append(ImportAction(relative_path, "create", "path is missing", content))
        elif not path.is_file():
            actions.append(ImportAction(relative_path, "invalid", "expected a file"))
        elif path.read_text(encoding="utf-8") == content:
            actions.append(ImportAction(relative_path, "keep", "content already matches"))
        else:
            actions.append(ImportAction(
                relative_path,
                "conflict",
                "existing provider configuration is preserved",
                content,
            ))
    metadata_path = project_dir / TOOL_GENERATED_PATH
    if metadata_path.is_file():
        try:
            metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
            previous_outputs = metadata.get("outputs", {})
        except (OSError, yaml.YAMLError):
            previous_outputs = {}
        if isinstance(previous_outputs, dict):
            for relative_path in sorted(set(previous_outputs) - set(expected)):
                path = project_dir / relative_path
                if path.is_file():
                    actions.append(ImportAction(
                        relative_path,
                        "conflict",
                        "previously managed output is no longer active; owner removal required",
                        None,
                    ))
    return ImportPlan(str(project_dir), actions)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, prefix=f".{path.name}."
    ) as handle:
        handle.write(content)
        staged = Path(handle.name)
    staged.replace(path)


def apply_tooling_plan(
    project_dir: Path,
    policy: ToolPolicy,
    plan: ImportPlan,
    conflict_resolutions: Optional[Dict[str, Optional[str]]] = None,
) -> List[str]:
    if plan.invalid:
        raise ValueError("Tooling plan contains invalid paths.")
    resolutions = conflict_resolutions or {}
    conflict_paths = {action.path for action in plan.conflicts}
    unknown_resolutions = sorted(set(resolutions) - conflict_paths)
    if unknown_resolutions:
        raise ValueError(
            "Tooling resolutions reference unknown conflicts: "
            + ", ".join(unknown_resolutions)
        )
    unresolved: List[str] = []
    proposal_root = project_dir / TOOLING_ROOT / "proposals"
    for action in plan.actions:
        if action.status == "create" and action.proposed_content is not None:
            path = project_dir / action.path
            if not path.exists():
                _atomic_write(path, action.proposed_content)
        elif action.status == "conflict":
            if action.proposed_content is not None:
                _atomic_write(proposal_root / action.path, action.proposed_content)
            if action.path in resolutions:
                resolution = resolutions[action.path]
                if resolution is None:
                    path = project_dir / action.path
                    if path.is_file():
                        path.unlink()
                else:
                    _atomic_write(project_dir / action.path, resolution)
            else:
                unresolved.append(action.path)

    effective_assets: Dict[str, str] = {}
    for relative_path in render_managed_assets(policy):
        path = project_dir / relative_path
        if path.is_file():
            effective_assets[relative_path] = path.read_text(encoding="utf-8")
    _atomic_write(project_dir / TOOL_POLICY_PATH, policy.to_yaml())
    _atomic_write(
        project_dir / TOOL_GENERATED_PATH,
        render_generated_metadata(policy, effective_assets),
    )
    incomplete = project_dir / TOOLING_ROOT / "INCOMPLETE"
    if unresolved:
        _atomic_write(
            incomplete,
            "Provider configuration conflicts require review:\n"
            + "".join(f"- {path}\n" for path in unresolved),
        )
    elif incomplete.exists():
        incomplete.unlink()
    return unresolved


def tooling_problems(project_dir: Path) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    incomplete = project_dir / TOOLING_ROOT / "INCOMPLETE"
    if incomplete.exists():
        errors.append(
            "tooling configuration is incomplete; review "
            f"{TOOLING_ROOT}/INCOMPLETE and {TOOLING_ROOT}/proposals"
        )
    try:
        policy = load_tool_policy(project_dir)
    except (OSError, ValueError) as exc:
        return [f"invalid tool policy: {exc}"], warnings

    metadata_path = project_dir / TOOL_GENERATED_PATH
    if not metadata_path.is_file():
        errors.append(f"missing tooling metadata: {TOOL_GENERATED_PATH}")
        return errors, warnings
    try:
        metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        if metadata.get("schema_version") != 1:
            raise ValueError("unsupported schema_version")
        outputs = metadata.get("outputs", {})
        if not isinstance(outputs, dict):
            raise ValueError("outputs must be a mapping")
        adapters = metadata.get("adapters", {})
        if not isinstance(adapters, dict):
            raise ValueError("adapters must be a mapping")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(f"invalid tooling metadata: {exc}")
        return errors, warnings

    if metadata.get("policy_sha256") != _sha256(policy.to_yaml()):
        warnings.append(
            "tool policy changed since provider assets were generated; "
            "run `factory tools plan`"
        )
    for tool in policy.enabled_tools:
        adapter = adapters.get(tool, {})
        if not isinstance(adapter, dict) or adapter.get("version") != ADAPTER_VERSION:
            warnings.append(f"tool adapter metadata is stale: {tool}")
    expected = render_managed_assets(policy)
    recorded_paths = set(outputs)
    for relative_path in sorted(recorded_paths - set(expected)):
        if (project_dir / relative_path).is_file():
            errors.append(
                f"stale managed tooling asset remains active: {relative_path}"
            )
    for relative_path, expected_content in expected.items():
        path = project_dir / relative_path
        if not path.is_file():
            errors.append(f"missing managed tooling asset: {relative_path}")
            continue
        actual = path.read_text(encoding="utf-8")
        recorded_hash = outputs.get(relative_path)
        if not recorded_hash:
            warnings.append(f"managed tooling asset is missing hash metadata: {relative_path}")
        elif recorded_hash != _sha256(actual):
            warnings.append(f"managed tooling asset drifted: {relative_path}")
        if policy.active and actual != expected_content:
            warnings.append(f"provider configuration differs from current policy: {relative_path}")
        configuration_problem = _configuration_problem(relative_path, actual)
        if configuration_problem:
            errors.append(
                f"invalid generated configuration {relative_path}: "
                f"{configuration_problem}"
            )
        if relative_path.endswith(".py"):
            try:
                compile(actual, relative_path, "exec")
            except SyntaxError as exc:
                errors.append(f"invalid generated hook {relative_path}: {exc}")

    if policy.level == "automation":
        observed_safe = any(
            name in {"test", "lint", "typecheck", "build", "format"}
            and command.command
            and command.evidence == "Observed"
            for name, command in policy.commands.items()
        )
        if not observed_safe:
            warnings.append(
                "automation kit has no Observed validation command; "
                "project command automation remains disabled"
            )
        if not policy.validate_on_stop:
            warnings.append(
                "automation kit validate-on-stop hook is disabled; Observed commands will not run"
            )
    return errors, list(dict.fromkeys(warnings))


def render_tooling_status(project_dir: Path, policy: ToolPolicy) -> str:
    errors, warnings = tooling_problems(project_dir)
    guard_status = (
        "enabled"
        if policy.active and policy.protect_factory_assets
        else "proposed"
        if policy.protect_factory_assets
        else "disabled"
    )
    stop_status = (
        "enabled"
        if policy.active and policy.validate_on_stop
        else "proposed"
        if policy.validate_on_stop
        else "disabled"
    )
    lines = [
        f"Tool kit: {policy.level} ({policy.status})",
        f"Enabled tools: {', '.join(policy.enabled_tools) or 'none'}",
        f"Factory asset guard: {guard_status}",
        f"Validate on stop: {stop_status}",
        f"Validation: {'failed' if errors else 'passed'}",
    ]
    lines.extend(f"  ERROR {message}" for message in errors)
    lines.extend(f"  WARN  {message}" for message in warnings)
    return "\n".join(lines)
