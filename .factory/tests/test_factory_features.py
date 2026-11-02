from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from factory_cli.adapters import AdapterError, CodexAdapter, GrokAdapter, normalize_output
from factory_cli.clarification import (
    load_clarification,
    save_clarification,
)
from factory_cli.discovery import scan_project
from factory_cli.dependencies import (
    DependencyError,
    apply_dependency_plan,
    create_dependency_plan,
    dependency_problems,
)
from factory_cli.guidance import (
    analyze_compatibility,
    apply_project_preset,
    command_suggestions,
)
from factory_cli.main import main, review_refined_sections
from factory_cli.models import FactoryConfig, ProjectIntake, TechChoice
from factory_cli.project import (
    apply_import,
    build_config,
    framework_root,
    initialize_project,
    plan_import,
    publish_specs,
    refine_specs,
)
from factory_cli.renderers import (
    render_bundle,
    render_confidence_review,
    render_project_specs,
)
from factory_cli.spec_sections import changed_sections, merge_sections
from factory_cli.stacks import automated_stacks, find_stack, stack_catalog_problems
from factory_cli.validation import inspect_project
from factory_cli.verification import (
    VerificationError,
    create_verification_plan,
    run_verification_plan,
    verification_problems,
)
from factory_cli.tooling import (
    CommandPolicy,
    PRE_TOOL_GUARD,
    ToolPolicy,
    apply_tooling_plan,
    default_tool_policy,
    overlay_tool_policy,
    parse_command_spec,
    plan_tooling,
    render_managed_assets,
    render_stop_validate,
    tooling_problems,
)


class ModelsAndRenderingTests(unittest.TestCase):
    def test_refinement_timeout_is_persisted_in_factory_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            intake = ProjectIntake(
                project_name="demo",
                tools=["codex"],
                refiner="codex",
                refinement_timeout_seconds=120,
            )
            config = build_config(intake)

            publish_specs(
                project_dir,
                intake,
                render_project_specs(intake),
                config=config,
            )

            persisted = FactoryConfig.from_yaml(
                (project_dir / ".factory-state" / "factory.yaml").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(persisted.default_refiner, "codex")
            self.assertEqual(persisted.refinement_timeout_seconds, 120)

    def test_preset_fills_only_blanks_as_proposed(self) -> None:
        intake = ProjectIntake(project_name="demo")
        intake.tech_stack["database"] = TechChoice("SQLite", "Approved")

        apply_project_preset(intake, "web-app")

        self.assertEqual(intake.project_preset, "web-app")
        self.assertEqual(intake.tech_stack["frontend"], TechChoice("Next.js", "Proposed"))
        self.assertEqual(intake.tech_stack["database"], TechChoice("SQLite", "Approved"))
        self.assertEqual(intake.commands["run"], "npm run dev")

    def test_compatibility_and_commands_are_stack_aware(self) -> None:
        intake = ProjectIntake(project_name="demo")
        intake.tech_stack["frontend"] = TechChoice("Next.js", "Preferred")
        intake.tech_stack["backend"] = TechChoice("Python + Django", "Proposed")

        insights = analyze_compatibility(intake)
        suggestions = command_suggestions(intake.tech_stack)

        self.assertTrue(any("Split-stack" in insight.title for insight in insights))
        self.assertEqual(insights[0].level, "info")
        self.assertIn("npm run dev", suggestions["run"])
        self.assertIn("python manage.py runserver", suggestions["run"])

    def test_project_specs_and_confidence_review_expose_unknowns(self) -> None:
        intake = ProjectIntake(project_name="demo", mvp_scope="Create account")
        intake.tech_stack["frontend"] = TechChoice("Next.js", "Proposed")
        intake.commands["test"] = "npm test"
        intake.refinement = {
            "assumptions": ["Accounts use email"],
            "open_questions": ["Who owns authentication?"],
        }

        markdown = render_project_specs(intake)
        review = render_confidence_review(intake)

        self.assertIn("## UX/UI Direction", markdown)
        self.assertIn("## Quality Attributes", markdown)
        self.assertIn("## Decision And Confidence Summary", markdown)
        self.assertIn("Next.js [Proposed]", review)
        self.assertIn("Accounts use email", review)
        self.assertIn("Who owns authentication?", review)

    def test_selective_section_merge_preserves_rejected_content(self) -> None:
        baseline = "# Project Specs\n\n## Summary\n\nBase\n\n## Scope\n\nBase scope\n"
        refined = "# Project Specs\n\n## Summary\n\nAI\n\n## Scope\n\nAI scope\n"

        self.assertEqual(changed_sections(baseline, refined), ["Summary", "Scope"])
        merged = merge_sections(baseline, refined, ["Summary"])

        self.assertIn("## Summary\n\nAI", merged)
        self.assertIn("## Scope\n\nBase scope", merged)

    def test_noninteractive_targeted_refinement_cannot_change_other_sections(self) -> None:
        intake = ProjectIntake(
            project_name="demo",
            refinement_sections=["technical"],
        )
        intake.refinement = {"status": "refined"}
        baseline = render_project_specs(intake)
        refined = baseline.replace("- Unknown", "- AI overview", 1).replace(
            "### Technology Stack",
            "### Technology Stack\n\nAI technical detail",
            1,
        )

        selected = review_refined_sections(intake, refined)

        self.assertNotIn("AI overview", selected)
        self.assertIn("AI technical detail", selected)
        self.assertEqual(intake.refinement["accepted_sections"], ["Technical Direction"])

    def test_approved_technology_creates_decision_and_expected_commands_remain_declared(self) -> None:
        intake = ProjectIntake(project_name="demo")
        intake.tech_stack["backend"] = TechChoice("FastAPI", "Approved")
        intake.commands["test"] = "pytest"
        config = FactoryConfig(enabled_tools=["codex", "cursor"], factory_link_mode="copy")

        bundle = render_bundle(intake, config)

        self.assertIn(".factory-state/decisions/DEC-0001-backend.md", bundle)
        self.assertNotIn(".claude/CLAUDE.md", bundle)
        self.assertIn("pytest [Expected]", bundle["project-specs.md"])
        self.assertIn("Approved", bundle["project.md"])

    def test_unapproved_technology_does_not_create_decision(self) -> None:
        intake = ProjectIntake(project_name="demo")
        intake.tech_stack["frontend"] = TechChoice("React", "Proposed")

        bundle = render_bundle(intake, FactoryConfig(factory_link_mode="copy"))

        self.assertFalse(any(path.startswith(".factory-state/decisions/DEC-") for path in bundle))

    def test_factory_config_rejects_refiner_that_is_not_enabled(self) -> None:
        config = FactoryConfig(enabled_tools=["cursor"], default_refiner="codex")
        with self.assertRaises(ValueError):
            config.to_yaml()

    def test_factory_config_rejects_unknown_schema(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported factory config schema"):
            FactoryConfig.from_yaml("schema_version: 99\n")

    def test_retired_config_keys_load_and_warn(self) -> None:
        config = FactoryConfig.from_yaml(
            "storage_backend: folder+postgres\n"
            "storage_dsn: postgres://db\n"
            "budget_enforcement: block\n"
            "budgets:\n"
            "  \"task:TASK-0001\": 1000\n"
        )
        warnings = config.ignored_setting_warnings()
        self.assertEqual(len(warnings), 4)
        self.assertTrue(any("folder+postgres" in item for item in warnings))


class ToolingTests(unittest.TestCase):
    def test_tool_policy_round_trip_and_active_assets(self) -> None:
        policy = default_tool_policy(["codex", "claude-code"], "guardrails")

        policy.commands["test"] = CommandPolicy(
            "npm test", "Expected", cwd="frontend", kind="test"
        )
        rendered = policy.to_yaml()
        self.assertIn("cwd: frontend", rendered)
        loaded = ToolPolicy.from_yaml(rendered)
        self.assertEqual(loaded.commands["test"].cwd, "frontend")
        self.assertEqual(loaded.commands["test"].kind, "test")
        bare = default_tool_policy(["codex"], "instructions")
        bare.commands["test"] = CommandPolicy("npm test")
        self.assertNotIn("cwd:", bare.to_yaml())
        self.assertNotIn("kind:", bare.to_yaml())
        assets = render_managed_assets(loaded)

        self.assertEqual(loaded.status, "approved")
        self.assertIn(".codex/config.toml", assets)
        self.assertIn(".codex/hooks.json", assets)
        self.assertIn(".claude/settings.json", assets)
        self.assertNotIn("danger-full-access", assets[".codex/config.toml"])
        self.assertNotIn("bypassPermissions", assets[".claude/settings.json"])

    def test_overlay_merges_commands_and_flips_inactive_level(self) -> None:
        policy = default_tool_policy(["codex"], "guardrails")
        policy.commands = {"test": CommandPolicy("npm test", "Observed")}
        updated = overlay_tool_policy(
            policy,
            level="instructions",
            commands={"format": "npm run format", "test": "npm test --watch"},
        )
        self.assertEqual(updated.level, "instructions")
        self.assertEqual(updated.status, "proposed")
        self.assertFalse(updated.protect_factory_assets)
        self.assertEqual(updated.commands["test"].command, "npm test --watch")
        self.assertEqual(updated.commands["test"].evidence, "Observed")
        self.assertEqual(updated.commands["format"].evidence, "Expected")
        self.assertEqual(parse_command_spec("analyze=flutter analyze"), ("analyze", "flutter analyze"))

    def test_instructions_kit_keeps_provider_configuration_inactive(self) -> None:
        assets = render_managed_assets(default_tool_policy(["codex"], "instructions"))

        self.assertNotIn(".codex/config.toml", assets)
        self.assertIn(
            ".factory-state/tooling/hooks/pre_tool_guard.py",
            assets,
        )

    def test_apply_preserves_conflict_and_validation_marks_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            policy = default_tool_policy(["codex"], "guardrails")
            config = project_dir / ".codex" / "config.toml"
            config.parent.mkdir()
            config.write_text("# owner config\n", encoding="utf-8")
            plan = plan_tooling(project_dir, policy)

            unresolved = apply_tooling_plan(project_dir, policy, plan)
            errors, _ = tooling_problems(project_dir)

            self.assertEqual(unresolved, [".codex/config.toml"])
            self.assertEqual(config.read_text(encoding="utf-8"), "# owner config\n")
            self.assertTrue(any("incomplete" in error for error in errors))

    def test_automation_embeds_only_observed_safe_commands(self) -> None:
        policy = default_tool_policy(["codex"], "automation")
        policy.commands = {
            "test": CommandPolicy("npm test", "Observed"),
            "lint": CommandPolicy("npm run lint", "Expected"),
            "install": CommandPolicy("npm install", "Observed"),
        }

        script = render_stop_validate(policy)

        compile(script, "stop_validate.py", "exec")
        self.assertIn("npm test", script)
        self.assertNotIn("npm run lint", script)
        self.assertNotIn("npm install", script)

    def test_downgrade_requires_reviewed_removal_of_active_provider_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            active = default_tool_policy(["codex"], "guardrails")
            first_plan = plan_tooling(project_dir, active)
            self.assertEqual(apply_tooling_plan(project_dir, active, first_plan), [])
            codex_config = project_dir / ".codex" / "config.toml"
            self.assertTrue(codex_config.is_file())

            inactive = default_tool_policy(["codex"], "instructions")
            inactive.status = "approved"
            downgrade = plan_tooling(project_dir, inactive)
            stale = [
                action.path
                for action in downgrade.conflicts
                if action.proposed_content is None
            ]
            self.assertIn(".codex/config.toml", stale)
            self.assertIn(".codex/hooks.json", stale)

            resolutions = {path: None for path in stale}
            self.assertEqual(
                apply_tooling_plan(project_dir, inactive, downgrade, resolutions),
                [],
            )
            self.assertFalse(codex_config.exists())
            errors, _ = tooling_problems(project_dir)
            self.assertEqual(errors, [])

    def test_pre_tool_guard_blocks_factory_write_but_allows_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            hook = Path(temp_dir) / "pre_tool_guard.py"
            hook.write_text(PRE_TOOL_GUARD, encoding="utf-8")

            blocked = subprocess.run(
                [sys.executable, str(hook)],
                input=json.dumps(
                    {"tool_name": "Bash", "tool_input": {"command": "rm -rf .factory"}}
                ),
                text=True,
                capture_output=True,
                check=False,
            )
            allowed = subprocess.run(
                [sys.executable, str(hook)],
                input=json.dumps(
                    {"tool_name": "Bash", "tool_input": {"command": "ls .factory"}}
                ),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(blocked.returncode, 2)
            self.assertIn("blocked", blocked.stderr)
            self.assertEqual(allowed.returncode, 0)

    def test_validation_rejects_malformed_provider_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            policy = default_tool_policy(["codex"], "guardrails")
            plan = plan_tooling(project_dir, policy)
            apply_tooling_plan(project_dir, policy, plan)
            (project_dir / ".codex" / "config.toml").write_text(
                'approval_policy = "unterminated\n',
                encoding="utf-8",
            )

            errors, warnings = tooling_problems(project_dir)

            self.assertTrue(any("invalid generated configuration" in item for item in errors))
            self.assertTrue(any("drifted" in item for item in warnings))


class DependencyTests(unittest.TestCase):
    def test_npm_workspace_uses_one_locked_root_install_and_keeps_unrelated_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "package.json").write_text(json.dumps({"workspaces": ["frontend", "packages/*"]}))
            (root / "package-lock.json").write_text("{}")
            for name in ("frontend", "packages/ui", "other"):
                directory = root / name
                directory.mkdir(parents=True)
                (directory / "package.json").write_text(json.dumps({"packageManager": "npm@10", "dependencies": {"react": "19"}}))
            with mock.patch("factory_cli.dependencies.service.shutil.which", return_value="/tools/npm"):
                plan = create_dependency_plan(root)
            self.assertTrue(plan.ready)
            self.assertEqual([c.working_dir for c in plan.commands], [".", "other"])
            self.assertEqual(plan.commands[0].argv[1:], ["ci", "--include=dev"])
            self.assertEqual(plan.commands[0].expected_paths, ["node_modules"])

    def test_npm_workspace_validates_hoisted_nested_and_missing_packages(self) -> None:
        from factory_cli.dependencies.service import _node_package_problems
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "package.json").write_text(json.dumps({"workspaces": {"packages": ["packages/*"]}}))
            (root / "package-lock.json").write_text("{}")
            member = root / "packages/ui"
            member.mkdir(parents=True)
            (member / "package.json").write_text(json.dumps({"dependencies": {"react": "19"}, "devDependencies": {"typescript": "6"}}))
            (root / "node_modules/react").mkdir(parents=True)
            (member / "node_modules/typescript").mkdir(parents=True)
            self.assertEqual(_node_package_problems(root, ".", "package.json"), [])
            (root / "node_modules/react").rmdir()
            errors = _node_package_problems(root, ".", "package.json")
            self.assertEqual(len(errors), 1)
            self.assertIn("react (packages/ui/package.json)", errors[0])
            (member / "package.json").write_text('{"dependencies": {"../unsafe": "1"}}')
            self.assertIn("invalid package name", _node_package_problems(root, ".", "package.json")[0])

    def test_plan_discovers_maven_dotnet_and_go_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            java = project_dir / "java"
            dotnet = project_dir / "dotnet"
            go = project_dir / "go"
            java.mkdir()
            dotnet.mkdir()
            go.mkdir()
            (java / "pom.xml").write_text("<project/>", encoding="utf-8")
            (java / "mvnw").write_text("#!/bin/sh\n", encoding="utf-8")
            (dotnet / "backend.csproj").write_text("<Project/>", encoding="utf-8")
            (go / "go.mod").write_text("module example\n", encoding="utf-8")

            with mock.patch(
                "factory_cli.dependencies.service.shutil.which",
                side_effect=lambda executable: f"/tools/{executable}",
            ):
                plan = create_dependency_plan(project_dir)

            self.assertTrue(plan.ready)
            self.assertEqual(
                [command.manager for command in plan.commands],
                ["maven", "dotnet", "go"],
            )
            self.assertEqual(plan.commands[0].argv[0], "./mvnw")
            self.assertEqual(plan.commands[1].argv[-1], "backend.csproj")
            self.assertEqual(plan.commands[2].argv[-2:], ["mod", "download"])

    def test_scaffold_provenance_selects_node_manager_without_manifest_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            frontend = project_dir / "frontend"
            frontend.mkdir()
            (frontend / "package.json").write_text(
                '{"dependencies":{}}',
                encoding="utf-8",
            )
            metadata = project_dir / ".factory-state" / "scaffolding" / "generated.yaml"
            metadata.parent.mkdir(parents=True)
            metadata.write_text(
                "outputs:\n"
                "  frontend/package.json:\n"
                "    adapter: vite\n",
                encoding="utf-8",
            )

            with mock.patch(
                "factory_cli.dependencies.service.shutil.which",
                return_value="/tools/npm",
            ):
                plan = create_dependency_plan(project_dir)

            self.assertTrue(plan.ready)
            self.assertEqual(plan.commands[0].manager, "npm")
            self.assertEqual(
                plan.commands[0].argv[-1],
                "--include=dev",
            )
            self.assertEqual(
                plan.commands[0].integrity_argv[-3:],
                ["ls", "--depth=0", "--include=dev"],
            )

    def test_plan_discovers_node_and_python_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            frontend = project_dir / "frontend"
            backend = project_dir / "backend"
            frontend.mkdir()
            backend.mkdir()
            (frontend / "package.json").write_text(
                '{"packageManager":"npm@10","dependencies":{}}',
                encoding="utf-8",
            )
            (backend / "pyproject.toml").write_text(
                '[project]\nname = "backend"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )

            with mock.patch(
                "factory_cli.dependencies.service.shutil.which",
                side_effect=lambda executable: (
                    "/tools/npm" if executable == "npm" else None
                ),
            ):
                plan = create_dependency_plan(project_dir)

            self.assertTrue(plan.ready)
            self.assertEqual(
                [command.manager for command in plan.commands],
                ["npm", "venv", "pip"],
            )
            self.assertEqual(plan.commands[0].working_dir, "frontend")
            self.assertFalse(plan.commands[1].requires_network)
            self.assertTrue(plan.requires_network)

    def test_apply_requires_network_approval_and_records_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            frontend = project_dir / "frontend"
            frontend.mkdir()
            manifest = frontend / "package.json"
            manifest.write_text(
                '{"packageManager":"npm@10","dependencies":{}}',
                encoding="utf-8",
            )
            npm = project_dir / "fake-npm"
            npm.write_text(
                "#!/bin/sh\n"
                "mkdir -p node_modules\n"
                "printf '%s\\n' '{\"lockfileVersion\":3}' > package-lock.json\n",
                encoding="utf-8",
            )
            npm.chmod(0o755)
            with mock.patch(
                "factory_cli.dependencies.service.shutil.which",
                return_value=str(npm),
            ):
                plan = create_dependency_plan(project_dir)

            with self.assertRaisesRegex(DependencyError, "network approval"):
                apply_dependency_plan(plan)
            self.assertFalse((frontend / "node_modules").exists())

            apply_dependency_plan(plan, allow_network=True)

            self.assertTrue((frontend / "node_modules").is_dir())
            self.assertTrue(
                (project_dir / ".factory-state" / "dependencies" / "installed.yaml").is_file()
            )
            self.assertEqual(dependency_problems(project_dir), ([], []))

            manifest.write_text(
                '{"packageManager":"npm@10","dependencies":{"new":"1"}}',
                encoding="utf-8",
            )
            errors, warnings = dependency_problems(project_dir)
            self.assertEqual(errors, [])
            self.assertTrue(any("changed" in warning for warning in warnings))

    def test_state_records_portable_commands_and_skips_build_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            frontend = project_dir / "frontend"
            frontend.mkdir()
            (frontend / "package.json").write_text(
                '{"packageManager":"npm@10","dependencies":{}}',
                encoding="utf-8",
            )
            npm = project_dir / "fake-npm"
            npm.write_text(
                "#!/bin/sh\n"
                "mkdir -p node_modules\n"
                "printf '%s\\n' '{\"lockfileVersion\":3}' > package-lock.json\n",
                encoding="utf-8",
            )
            npm.chmod(0o755)
            with mock.patch(
                "factory_cli.dependencies.service.shutil.which",
                return_value=str(npm),
            ):
                plan = create_dependency_plan(project_dir)
            apply_dependency_plan(plan, allow_network=True)

            state = (
                project_dir / ".factory-state" / "dependencies" / "installed.yaml"
            ).read_text(encoding="utf-8")
            self.assertNotIn(str(npm), state)
            self.assertIn("- fake-npm", state)

            # a build copies a package.json into dist/: not a project manifest
            dist = frontend / "dist" / "cjs"
            dist.mkdir(parents=True)
            (dist / "package.json").write_text('{"type":"commonjs"}', encoding="utf-8")
            self.assertEqual(dependency_problems(project_dir), ([], []))

    def test_npm_install_rejects_missing_declared_development_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            frontend = project_dir / "frontend"
            frontend.mkdir()
            (frontend / "package.json").write_text(
                '{"packageManager":"npm@10","devDependencies":{"vite":"1"}}',
                encoding="utf-8",
            )
            npm = project_dir / "fake-npm"
            npm.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = \"ls\" ]; then exit 0; fi\n"
                "mkdir -p node_modules\n",
                encoding="utf-8",
            )
            npm.chmod(0o755)
            with mock.patch(
                "factory_cli.dependencies.service.shutil.which",
                return_value=str(npm),
            ):
                plan = create_dependency_plan(project_dir)

            self.assertIn("--include=dev", plan.commands[0].argv)
            with self.assertRaisesRegex(
                DependencyError,
                "missing installed devDependencies package: vite",
            ):
                apply_dependency_plan(plan, allow_network=True)

            self.assertTrue(
                (project_dir / ".factory-state" / "dependencies" / "INCOMPLETE").is_file()
            )

    def test_validation_detects_dependency_tree_drift_after_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            frontend = project_dir / "frontend"
            frontend.mkdir()
            (frontend / "package.json").write_text(
                '{"packageManager":"npm@10","dependencies":{"react":"1"},'
                '"devDependencies":{"vite":"1"}}',
                encoding="utf-8",
            )
            npm = project_dir / "fake-npm"
            npm.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = \"ls\" ]; then exit 0; fi\n"
                "mkdir -p node_modules/react node_modules/vite\n",
                encoding="utf-8",
            )
            npm.chmod(0o755)
            with mock.patch(
                "factory_cli.dependencies.service.shutil.which",
                return_value=str(npm),
            ):
                plan = create_dependency_plan(project_dir)

            apply_dependency_plan(plan, allow_network=True)
            self.assertEqual(dependency_problems(project_dir), ([], []))

            npm.write_text(
                "#!/bin/sh\n"
                "printf '%s' 'missing transitive dependency' >&2\n"
                "exit 1\n",
                encoding="utf-8",
            )
            with mock.patch(
                "factory_cli.dependencies.service.shutil.which",
                return_value=str(npm),
            ):
                integrity_errors, _ = dependency_problems(
                    project_dir,
                    check_integrity=True,
                )
            self.assertTrue(
                any("missing transitive dependency" in error for error in integrity_errors)
            )

            (frontend / "node_modules" / "vite").rmdir()
            errors, _ = dependency_problems(project_dir)

            self.assertTrue(
                any(
                    "missing installed devDependencies package: vite" in error
                    for error in errors
                )
            )

    def test_failed_install_keeps_source_and_records_incomplete_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            frontend = project_dir / "frontend"
            frontend.mkdir()
            manifest = frontend / "package.json"
            original = '{"packageManager":"npm@10","dependencies":{}}'
            manifest.write_text(original, encoding="utf-8")
            npm = project_dir / "fake-npm"
            npm.write_text(
                "#!/bin/sh\nmkdir -p node_modules\nprintf '%s' 'registry down' >&2\nexit 3\n",
                encoding="utf-8",
            )
            npm.chmod(0o755)
            with mock.patch(
                "factory_cli.dependencies.service.shutil.which",
                return_value=str(npm),
            ):
                plan = create_dependency_plan(project_dir)

            with self.assertRaisesRegex(DependencyError, "registry down"):
                apply_dependency_plan(plan, allow_network=True)

            self.assertEqual(manifest.read_text(encoding="utf-8"), original)
            self.assertTrue(
                (project_dir / ".factory-state" / "dependencies" / "INCOMPLETE").is_file()
            )
            errors, _ = dependency_problems(project_dir)
            self.assertTrue(any("incomplete" in error for error in errors))

    def test_apply_rejects_manifest_changes_after_planning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            manifest = project_dir / "package.json"
            manifest.write_text(
                '{"packageManager":"npm@10","dependencies":{}}',
                encoding="utf-8",
            )
            marker = project_dir / "command-ran"
            npm = project_dir / "fake-npm"
            npm.write_text(
                "#!/bin/sh\ntouch command-ran\nmkdir -p node_modules\n",
                encoding="utf-8",
            )
            npm.chmod(0o755)
            with mock.patch(
                "factory_cli.dependencies.service.shutil.which",
                return_value=str(npm),
            ):
                plan = create_dependency_plan(project_dir)

            manifest.write_text(
                '{"packageManager":"npm@10","dependencies":{"changed":"1"}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DependencyError, "changed after planning"):
                apply_dependency_plan(plan, allow_network=True)

            self.assertFalse(marker.exists())
            self.assertFalse(
                (project_dir / ".factory-state" / "dependencies").exists()
            )

    def test_plan_reports_missing_or_ambiguous_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            empty = create_dependency_plan(project_dir)
            self.assertFalse(empty.ready)
            self.assertTrue(any("no supported" in error for error in empty.errors))

            (project_dir / "package.json").write_text("{}", encoding="utf-8")
            ambiguous = create_dependency_plan(project_dir)
            self.assertFalse(ambiguous.ready)
            self.assertTrue(any("package manager is unknown" in error for error in ambiguous.errors))

            (project_dir / "package-lock.json").write_text("{}", encoding="utf-8")
            (project_dir / "pnpm-lock.yaml").write_text("lockfileVersion: 9", encoding="utf-8")
            conflicting = create_dependency_plan(project_dir)
            self.assertFalse(conflicting.ready)
            self.assertTrue(any("conflicting lockfiles" in error for error in conflicting.errors))

    def test_validation_rejects_unsafe_dependency_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            metadata = project_dir / ".factory-state" / "dependencies" / "installed.yaml"
            metadata.parent.mkdir(parents=True)
            metadata.write_text(
                "schema_version: 1\n"
                "status: installed\n"
                "inputs: {}\n"
                "commands:\n"
                "  - status: observed\n"
                "    expected_paths:\n"
                "      - ../../outside\n",
                encoding="utf-8",
            )

            errors, _ = dependency_problems(project_dir)

            self.assertTrue(any("invalid dependency environment" in error for error in errors))



class VerificationTests(unittest.TestCase):
    def test_plan_discovers_manifest_checks_and_respects_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            frontend = project_dir / "frontend"
            backend = project_dir / "backend"
            frontend.mkdir()
            backend.mkdir()
            (frontend / "package.json").write_text(
                '{"packageManager":"npm@10","scripts":{"test":"vitest","build":"vite build"}}',
                encoding="utf-8",
            )
            (backend / "pyproject.toml").write_text(
                '[project.optional-dependencies]\ntest = ["pytest"]\n',
                encoding="utf-8",
            )
            (backend / "tests").mkdir()
            python = backend / ".venv" / "bin" / "python"
            python.parent.mkdir(parents=True)
            python.write_text("", encoding="utf-8")

            with mock.patch(
                "factory_cli.verification.service.shutil.which",
                return_value="/tools/npm",
            ):
                quick = create_verification_plan(project_dir)
                full = create_verification_plan(project_dir, profile="full")

            self.assertTrue(quick.ready)
            self.assertEqual([check.kind for check in quick.checks], ["test", "test"])
            self.assertEqual(
                [check.kind for check in full.checks],
                ["test", "build", "test"],
            )
            self.assertNotIn("shell", quick.render())
            self.assertNotIn("/tools/npm", quick.render())

    def test_run_records_failure_then_success_without_persisting_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / "package.json").write_text(
                '{"packageManager":"npm@10","scripts":{"test":"test","lint":"lint"}}',
                encoding="utf-8",
            )
            npm = project_dir / "fake-npm"
            npm.write_text(
                "#!/bin/sh\n"
                "if [ \"$2\" = \"lint\" ]; then printf '%s' 'lint failed'; exit 3; fi\n",
                encoding="utf-8",
            )
            npm.chmod(0o755)
            with mock.patch(
                "factory_cli.verification.service.shutil.which",
                return_value=str(npm),
            ):
                plan = create_verification_plan(project_dir)
                results = run_verification_plan(plan)

            self.assertEqual(
                [result.status for result in results],
                ["failed", "passed"],
            )
            errors, warnings = verification_problems(project_dir)
            self.assertTrue(any("failed" in error for error in errors))
            self.assertEqual(warnings, [])
            metadata = (
                project_dir / ".factory-state" / "verification" / "latest.yaml"
            ).read_text(encoding="utf-8")
            self.assertNotIn("lint failed", metadata)
            self.assertNotIn("inputs:", metadata)
            self.assertNotIn("output_sha256", metadata)
            self.assertNotIn(str(npm), metadata)
            self.assertIn("command: npm run lint", metadata)
            self.assertFalse(
                (project_dir / ".factory-state" / "verification" / "runs").exists()
            )

            npm.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            npm.chmod(0o755)
            with mock.patch(
                "factory_cli.verification.service.shutil.which",
                return_value=str(npm),
            ):
                passing = create_verification_plan(project_dir)
                results = run_verification_plan(passing)

            self.assertTrue(all(result.status == "passed" for result in results))
            self.assertEqual(verification_problems(project_dir), ([], []))

    def test_run_keeps_evidence_stable_when_source_text_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            manifest = project_dir / "package.json"
            manifest.write_text(
                '{"packageManager":"npm@10","scripts":{"test":"test"}}',
                encoding="utf-8",
            )
            npm = project_dir / "fake-npm"
            npm.write_text("#!/bin/sh\ntouch command-ran\n", encoding="utf-8")
            npm.chmod(0o755)
            with mock.patch(
                "factory_cli.verification.service.shutil.which",
                return_value=str(npm),
            ):
                plan = create_verification_plan(project_dir)

            (project_dir / "src.py").write_text("print('ok')\n", encoding="utf-8")
            manifest.write_text(
                '{"packageManager":"npm@10","scripts":{"test":"changed"}}',
                encoding="utf-8",
            )
            with mock.patch(
                "factory_cli.verification.service.shutil.which",
                return_value=str(npm),
            ):
                run_verification_plan(plan)

            self.assertTrue((project_dir / "command-ran").exists())
            metadata = (
                project_dir / ".factory-state" / "verification" / "latest.yaml"
            ).read_text(encoding="utf-8")
            self.assertNotIn("inputs:", metadata)
            self.assertNotIn("source_sha256", metadata)
            self.assertNotIn(str(npm), metadata)

    def test_run_rejects_when_discovered_commands_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            manifest = project_dir / "package.json"
            manifest.write_text(
                '{"packageManager":"npm@10","scripts":{"test":"test"}}',
                encoding="utf-8",
            )
            npm = project_dir / "fake-npm"
            npm.write_text("#!/bin/sh\ntouch command-ran\n", encoding="utf-8")
            npm.chmod(0o755)
            with mock.patch(
                "factory_cli.verification.service.shutil.which",
                return_value=str(npm),
            ):
                plan = create_verification_plan(project_dir)
            manifest.write_text(
                '{"packageManager":"npm@10","scripts":{}}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(VerificationError, "changed after planning"):
                run_verification_plan(plan)

            self.assertFalse((project_dir / "command-ran").exists())
            self.assertFalse((project_dir / ".factory-state").exists())

    def test_policy_commands_replace_manifest_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / "frontend").mkdir()
            (project_dir / "package.json").write_text(
                '{"packageManager":"npm@10","scripts":{"test":"vitest","build":"vite build"}}',
                encoding="utf-8",
            )
            policy = project_dir / ".factory-state" / "tooling" / "tool-policy.yaml"
            policy.parent.mkdir(parents=True)
            policy.write_text(
                "commands:\n"
                "  test:\n"
                "    command: npm run test\n"
                "    evidence: Expected\n"
                "  frontend-build:\n"
                "    command: npm run build\n"
                "    cwd: frontend\n"
                "    kind: build\n"
                "    evidence: Expected\n"
                "  format:\n"
                "    command: npm run format\n"
                "    evidence: Expected\n",
                encoding="utf-8",
            )
            with mock.patch(
                "factory_cli.verification.service.shutil.which",
                return_value="/tools/npm",
            ):
                quick = create_verification_plan(project_dir)
                full = create_verification_plan(project_dir, profile="full")

            self.assertEqual(quick.origin, "policy")
            self.assertEqual([check.kind for check in quick.checks], ["format", "test"])
            self.assertEqual(
                [check.kind for check in full.checks],
                ["format", "test", "build"],
            )
            build = next(check for check in full.checks if check.kind == "build")
            self.assertEqual(build.working_dir, "frontend")
            self.assertEqual(build.command_display, "npm run build")
            self.assertNotIn("/tools/npm", full.render())

    def test_absolute_policy_command_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            policy = project_dir / ".factory-state" / "tooling" / "tool-policy.yaml"
            policy.parent.mkdir(parents=True)
            policy.write_text(
                "commands:\n"
                "  test:\n"
                "    command: /usr/bin/npm test\n"
                "    evidence: Expected\n",
                encoding="utf-8",
            )
            plan = create_verification_plan(project_dir)
            self.assertFalse(plan.ready)
            self.assertTrue(any("absolute" in error for error in plan.errors))

    def test_quick_run_records_full_discovery_into_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / "package.json").write_text(
                '{"packageManager":"npm@10","scripts":{"test":"vitest","build":"vite build"}}',
                encoding="utf-8",
            )
            npm = project_dir / "fake-npm"
            npm.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            npm.chmod(0o755)
            policy = project_dir / ".factory-state" / "tooling" / "tool-policy.yaml"
            policy.parent.mkdir(parents=True)
            policy.write_text(
                "commands:\n"
                "  install:\n"
                "    command: npm install\n"
                "    evidence: Expected\n",
                encoding="utf-8",
            )
            with mock.patch(
                "factory_cli.verification.service.shutil.which",
                return_value=str(npm),
            ):
                plan = create_verification_plan(project_dir, profile="quick")
                results = run_verification_plan(plan)

            self.assertEqual([result.check.kind for result in results], ["test"])
            recorded = policy.read_text(encoding="utf-8")
            self.assertIn("npm install", recorded)
            self.assertIn("npm run test", recorded)
            self.assertIn("npm run build", recorded)
            self.assertNotIn(str(npm), recorded)
            metadata = (
                project_dir / ".factory-state" / "verification" / "latest.yaml"
            ).read_text(encoding="utf-8")
            self.assertIn("tool-policy.yaml", metadata)
            self.assertNotIn("inputs:", metadata)
            self.assertFalse(
                (project_dir / ".factory-state" / "verification" / "runs").exists()
            )

    def test_legacy_evidence_warns_without_failing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            metadata = project_dir / ".factory-state" / "verification" / "latest.yaml"
            metadata.parent.mkdir(parents=True)
            metadata.write_text(
                "schema_version: 1\n"
                "status: passed\n"
                "inputs:\n"
                "  package.json: abc\n"
                "results:\n"
                "- status: passed\n"
                "  argv:\n"
                "  - /usr/bin/npm\n"
                "  - run\n"
                "  - test\n",
                encoding="utf-8",
            )
            (project_dir / "package.json").write_text("{}\n", encoding="utf-8")
            errors, warnings = verification_problems(project_dir)
            self.assertEqual(errors, [])
            self.assertEqual(len(warnings), 1)
            self.assertIn("absolute", warnings[0])


    def test_policy_timeout_round_trips_and_wins_over_the_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            policy = project_dir / ".factory-state" / "tooling" / "tool-policy.yaml"
            policy.parent.mkdir(parents=True)
            policy.write_text(
                "commands:\n"
                "  test:\n"
                "    command: npm run test\n"
                "    timeout: 900\n"
                "    evidence: Expected\n"
                "  lint:\n"
                "    command: npm run lint\n"
                "    evidence: Expected\n",
                encoding="utf-8",
            )
            loaded = ToolPolicy.from_yaml(policy.read_text(encoding="utf-8"))
            self.assertEqual(loaded.commands["test"].timeout, 900)
            self.assertIn("timeout: 900", loaded.to_yaml())
            self.assertNotIn("timeout", loaded.to_yaml().split("lint:")[1])

            completed = subprocess.CompletedProcess([], 0, "", "")
            with mock.patch(
                "factory_cli.verification.service.shutil.which",
                return_value="/tools/npm",
            ):
                plan = create_verification_plan(project_dir)
                self.assertIn("timeout: 900s", plan.render())
                for default, expected in ((None, {"lint": 300}), (50, {"lint": 50})):
                    with mock.patch(
                        "factory_cli.verification.service.subprocess.run",
                        return_value=completed,
                    ) as run:
                        run_verification_plan(plan, timeout_seconds=default)
                    timeouts = {
                        call.args[0][-1]: call.kwargs["timeout"] for call in run.call_args_list
                    }
                    self.assertEqual(timeouts, {"test": 900, **expected})

    def test_invalid_policy_timeout_is_rejected(self) -> None:
        for value in ("-1", "ten", "true", "1.5"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as temp_dir:
                project_dir = Path(temp_dir)
                policy = project_dir / ".factory-state" / "tooling" / "tool-policy.yaml"
                policy.parent.mkdir(parents=True)
                policy.write_text(
                    "commands:\n"
                    "  test:\n"
                    "    command: npm run test\n"
                    f"    timeout: {value}\n"
                    "    evidence: Expected\n",
                    encoding="utf-8",
                )
                plan = create_verification_plan(project_dir)
                self.assertFalse(plan.ready)
                self.assertTrue(any("timeout" in error for error in plan.errors))

    def test_a_timed_out_check_names_the_setting_to_raise(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            policy = project_dir / ".factory-state" / "tooling" / "tool-policy.yaml"
            policy.parent.mkdir(parents=True)
            policy.write_text(
                "commands:\n  test:\n    command: npm run test\n    evidence: Expected\n",
                encoding="utf-8",
            )
            with mock.patch(
                "factory_cli.verification.service.shutil.which",
                return_value="/tools/npm",
            ), mock.patch(
                "factory_cli.verification.service.subprocess.run",
                side_effect=subprocess.TimeoutExpired(["npm"], 300),
            ):
                plan = create_verification_plan(project_dir)
                [result] = run_verification_plan(plan)

            self.assertEqual(result.status, "failed")
            self.assertIn("timed out after 300 seconds", result.error)
            self.assertIn("tool-policy.yaml", result.error)
            self.assertIn("--timeout", result.error)

    def test_discovered_checks_of_one_kind_in_one_directory_get_their_own_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / "package.json").write_text(
                '{"packageManager":"npm@10","scripts":{"test":"vitest","build":"vite build"}}',
                encoding="utf-8",
            )
            (project_dir / "pyproject.toml").write_text(
                '[project]\nname = "demo"\n[tool.pytest.ini_options]\n',
                encoding="utf-8",
            )
            python = project_dir / ".venv" / "bin" / "python"
            python.parent.mkdir(parents=True)
            python.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            python.chmod(0o755)
            npm = project_dir / "fake-npm"
            npm.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            npm.chmod(0o755)
            policy = project_dir / ".factory-state" / "tooling" / "tool-policy.yaml"
            policy.parent.mkdir(parents=True)
            policy.write_text(
                "commands:\n"
                "  build:\n"
                "    command: ''\n"
                "    evidence: Expected\n"
                "  test-python:\n"
                "    command: make py\n"
                "    evidence: Expected\n",
                encoding="utf-8",
            )
            with mock.patch(
                "factory_cli.verification.service.shutil.which",
                return_value=str(npm),
            ):
                plan = create_verification_plan(project_dir, profile="full")
                self.assertEqual(plan.origin, "discovery")
                results = run_verification_plan(plan)

            self.assertEqual([result.status for result in results], ["passed"] * 3)
            commands = ToolPolicy.from_yaml(policy.read_text(encoding="utf-8")).commands
            self.assertEqual(commands["test"].command, "npm run test")
            self.assertEqual(commands["build"].command, "npm run build")
            self.assertEqual(commands["test-python"].command, "make py")
            self.assertEqual(commands["test-python-2"].command, ".venv/bin/python -m pytest")
            self.assertEqual(commands["test-python-2"].kind, "test")

class AdapterTests(unittest.TestCase):
    @staticmethod
    def executable(root: Path, content: str) -> Path:
        executable = root / "fake-codex"
        executable.write_text(content, encoding="utf-8")
        executable.chmod(0o755)
        return executable

    def test_normalize_output_accepts_provider_result_wrapper(self) -> None:
        result = normalize_output(
            '{"result":"{\\"markdown\\":\\"# Project Specs\\\\n\\",\\"assumptions\\":[],\\"open_questions\\":[]}"}'
        )
        self.assertTrue(result.markdown.startswith("# Project Specs"))

    def test_normalize_output_rejects_invalid_json(self) -> None:
        with self.assertRaises(AdapterError):
            normalize_output("not json")

    def test_normalize_output_rejects_malformed_schema(self) -> None:
        with self.assertRaisesRegex(AdapterError, "must be arrays"):
            normalize_output(
                '{"markdown":"# Project Specs\\n","assumptions":"none","open_questions":[]}'
            )

    def test_adapter_runs_in_isolated_temporary_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = self.executable(
                Path(temp_dir),
                "#!/bin/sh\n"
                "test -f intake.yaml || exit 2\n"
                "test -f template.md || exit 3\n"
                "printf '%s' '{\"markdown\":\"# Project Specs\\n\",\"assumptions\":[],\"open_questions\":[]}'\n",
            )
            with mock.patch.object(CodexAdapter, "detect", return_value=str(executable)):
                result = CodexAdapter().refine(
                    "project_name: demo\n", "# Project Specs\n"
                )

        self.assertTrue(result.markdown.startswith("# Project Specs"))
        command = CodexAdapter().command(
            "codex", "prompt", Path("result.json"), Path("schema.json")
        )
        self.assertIn("read-only", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("--json", command)
        self.assertIn("--output-schema", command)
        self.assertIn("--output-last-message", command)

        with tempfile.TemporaryDirectory() as schema_dir:
            schema = Path(schema_dir) / "schema.json"
            schema.write_text('{"type":"object"}', encoding="utf-8")
            grok = GrokAdapter().command("grok", "prompt", None, schema)
        self.assertEqual(grok[0], "grok")
        self.assertIn("--single", grok)
        self.assertIn("read-only", grok)
        self.assertIn("plan", grok)
        self.assertIn("--json-schema", grok)
        self.assertIn('{"type":"object"}', grok)

    def test_codex_adapter_streams_jsonl_progress_and_reads_final_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = self.executable(
                Path(temp_dir),
                "#!/bin/sh\n"
                "output=''\n"
                "while [ \"$#\" -gt 0 ]; do\n"
                "  if [ \"$1\" = '--output-last-message' ]; then\n"
                "    shift\n"
                "    output=$1\n"
                "  fi\n"
                "  shift\n"
                "done\n"
                "printf '%s\\n' '{\"type\":\"thread.started\"}'\n"
                "printf '%s\\n' '{\"type\":\"turn.started\"}'\n"
                "printf '%s' '{\"markdown\":\"# Project Specs\\n\",\"assumptions\":[],\"open_questions\":[]}' > \"$output\"\n",
            )
            progress = []
            with mock.patch.object(CodexAdapter, "detect", return_value=str(executable)):
                result = CodexAdapter().refine(
                    "project_name: demo\n",
                    "# Project Specs\n",
                    progress=progress.append,
                )

        self.assertTrue(result.markdown.startswith("# Project Specs"))
        self.assertTrue(any("session started" in item.lower() for item in progress))
        self.assertTrue(any("analyzing" in item.lower() for item in progress))
        self.assertTrue(any("validating" in item.lower() for item in progress))

    def test_real_refinement_process_cannot_write_project_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project_dir = root / "project"
            project_dir.mkdir()
            sentinel = project_dir / "sentinel.txt"
            sentinel.write_text("unchanged\n", encoding="utf-8")
            executable = root / "fake-codex"
            executable.write_text(
                "#!/bin/sh\n"
                "printf 'temporary' > attempted-write.txt\n"
                "printf '%s' '{\"markdown\":\"# Project Specs\\n\",\"assumptions\":[],\"open_questions\":[]}'\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)

            with mock.patch.object(CodexAdapter, "detect", return_value=str(executable)):
                CodexAdapter().refine("project_name: demo\n", "# Project Specs\n")

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged\n")
            self.assertEqual([path.name for path in project_dir.iterdir()], ["sentinel.txt"])

    def test_deterministic_refinement_is_available_without_ai(self) -> None:
        intake = ProjectIntake(project_name="demo", use_ai=False)
        markdown, warning = refine_specs(intake)
        self.assertIsNone(warning)
        self.assertEqual(markdown, render_project_specs(intake))
        self.assertEqual(intake.refinement["status"], "deterministic")
        self.assertIn("timestamp", intake.refinement)
        self.assertEqual(len(intake.refinement["input_sha256"]), 64)
        self.assertEqual(len(intake.refinement["output_sha256"]), 64)

    @mock.patch("factory_cli.adapters.shutil.which", return_value=None)
    def test_adapter_reports_missing_cli(self, _which) -> None:
        with self.assertRaisesRegex(AdapterError, "not installed"):
            CodexAdapter().refine("project_name: demo\n", "# Project Specs\n")

    def test_adapter_reports_authentication_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = self.executable(
                Path(temp_dir),
                "#!/bin/sh\nprintf '%s' 'authentication required' >&2\nexit 1\n",
            )
            with mock.patch.object(CodexAdapter, "detect", return_value=str(executable)):
                with self.assertRaisesRegex(AdapterError, "authentication required"):
                    CodexAdapter().refine(
                        "project_name: demo\n", "# Project Specs\n"
                    )

    def test_adapter_reports_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = self.executable(Path(temp_dir), "#!/bin/sh\nexec sleep 10\n")
            with mock.patch.object(CodexAdapter, "detect", return_value=str(executable)):
                with self.assertRaisesRegex(AdapterError, "timed out"):
                    CodexAdapter().refine(
                        "project_name: demo\n",
                        "# Project Specs\n",
                        timeout=0.1,
                    )

    def test_adapter_supports_cancellation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = self.executable(Path(temp_dir), "#!/bin/sh\nexec sleep 10\n")
            cancel_event = threading.Event()
            timer = threading.Timer(0.1, cancel_event.set)
            timer.start()
            try:
                with mock.patch.object(
                    CodexAdapter, "detect", return_value=str(executable)
                ):
                    with self.assertRaisesRegex(AdapterError, "cancelled"):
                        CodexAdapter().refine(
                            "project_name: demo\n",
                            "# Project Specs\n",
                            cancel_event=cancel_event,
                        )
            finally:
                timer.cancel()


class ImportTests(unittest.TestCase):
    def test_scanner_discovers_layout_and_expected_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / "src").mkdir()
            (project_dir / "tests").mkdir()
            (project_dir / "package.json").write_text(
                '{"scripts":{"dev":"vite","test":"vitest","lint":"eslint ."}}',
                encoding="utf-8",
            )

            scan = scan_project(project_dir)

            self.assertIn("package.json", scan.manifests)
            self.assertEqual(scan.source_directories, ["src"])
            self.assertEqual(scan.test_directories, ["tests"])
            self.assertEqual(scan.commands["run"], "npm run dev")
            self.assertEqual(scan.commands["test"], "npm run test")

    def test_import_preview_is_read_only_and_apply_creates_valid_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "existing"
            project_dir.mkdir()
            (project_dir / "README.md").write_text("# Existing\n", encoding="utf-8")
            before = sorted(path.relative_to(project_dir) for path in project_dir.rglob("*"))

            plan = plan_import(project_dir, framework_root())
            after_preview = sorted(path.relative_to(project_dir) for path in project_dir.rglob("*"))
            self.assertEqual(before, after_preview)
            self.assertFalse(plan.invalid)

            apply_import(plan, framework_root(), force_copy=True)
            self.assertTrue((project_dir / ".factory" / "AGENTS.md").exists())
            self.assertTrue((project_dir / ".factory-state" / "factory.yaml").exists())
            self.assertEqual(main(["validate", str(project_dir)]), 0)

    def test_import_preserves_instruction_conflict_and_marks_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "existing"
            project_dir.mkdir()
            original = "# Existing project instructions\n"
            (project_dir / "AGENTS.md").write_text(original, encoding="utf-8")

            plan = plan_import(project_dir, framework_root())
            apply_import(plan, framework_root(), force_copy=True)

            self.assertEqual((project_dir / "AGENTS.md").read_text(encoding="utf-8"), original)
            self.assertTrue(
                (project_dir / ".factory-state" / "import" / "proposals" / "AGENTS.md").exists()
            )
            self.assertTrue((project_dir / ".factory-state" / "import" / "INCOMPLETE").exists())

    def test_owner_reviewed_instruction_merge_completes_import(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "existing"
            project_dir.mkdir()
            (project_dir / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
            plan = plan_import(project_dir, framework_root())

            apply_import(
                plan,
                framework_root(),
                force_copy=True,
                conflict_resolutions={"AGENTS.md": "# Reviewed merge\n"},
            )

            self.assertEqual(
                (project_dir / "AGENTS.md").read_text(encoding="utf-8"),
                "# Reviewed merge\n",
            )
            self.assertFalse((project_dir / ".factory-state" / "import" / "INCOMPLETE").exists())
            self.assertTrue(
                (project_dir / ".factory-state" / "import" / "proposals" / "AGENTS.md").exists()
            )

    def test_import_requires_resolution_of_existing_tool_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "existing"
            policy = project_dir / ".factory-state" / "tooling" / "tool-policy.yaml"
            policy.parent.mkdir(parents=True)
            policy.write_text("schema_version: 99\n", encoding="utf-8")

            plan = plan_import(project_dir, framework_root())
            apply_import(plan, framework_root(), force_copy=True)

            self.assertTrue(
                (project_dir / ".factory-state" / "import" / "INCOMPLETE").is_file()
            )
            self.assertTrue(
                (
                    project_dir
                    / ".factory-state"
                    / "import"
                    / "proposals"
                    / ".factory-state"
                    / "tooling"
                    / "tool-policy.yaml"
                ).is_file()
            )

    def test_import_recognizes_uninitialized_configured_submodule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            (project_dir / ".factory").mkdir()
            (project_dir / ".gitmodules").write_text(
                '[submodule ".factory"]\n\tpath = .factory\n\turl = ../factory.git\n',
                encoding="utf-8",
            )

            plan = plan_import(project_dir, framework_root())
            factory_action = next(action for action in plan.actions if action.path == ".factory")

            self.assertEqual(factory_action.status, "create")
            self.assertIn("uninitialized", factory_action.reason)


class ClarificationTests(unittest.TestCase):
    def _artifact(self, path: Path) -> None:
        path.write_text(
            """---
schema_version: 1
id: CLAR-0001
task_id: TASK-0002
status: open
source_artifacts: []
created: '2026-06-18'
updated: '2026-06-18'
answered_at: null
questions:
- id: mode
  type: single_choice
  prompt: Choose a mode
  required: true
  context: ''
  recommendation: safe
  options:
  - value: safe
    label: Safe
  - value: fast
    label: Fast
  depends_on: null
- id: notes
  type: free_text
  prompt: Explain the fast mode
  required: true
  context: ''
  recommendation: ''
  options: []
  depends_on:
    question: mode
    equals: fast
answers: {}
---
# Clarification
""",
            encoding="utf-8",
        )

    def test_conditional_required_question_only_applies_when_active(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "CLAR-0001.md"
            self._artifact(path)
            clarification = load_clarification(path)
            self.assertEqual(clarification.missing_required({"mode": "safe", "notes": ""}), [])
            self.assertEqual(
                clarification.missing_required({"mode": "fast", "notes": ""}), ["notes"]
            )

    def test_save_and_submit_are_durable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "CLAR-0001.md"
            self._artifact(path)
            clarification = load_clarification(path)
            save_clarification(clarification, {"mode": "safe", "notes": ""}, submit=True)
            reloaded = load_clarification(path)
            self.assertEqual(reloaded.status, "answered")
            self.assertEqual(reloaded.answers["mode"], "safe")

    def test_project_validation_warns_but_does_not_fail_for_open_clarification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir, _ = initialize_project(
                "demo",
                Path(temp_dir),
                framework_root(),
                force_copy=True,
            )
            path = project_dir / ".factory-state" / "artifacts" / "CLAR-0001-TASK-0002.md"
            self._artifact(path)

            report = inspect_project(project_dir)

            self.assertTrue(report.passed)
            self.assertTrue(any("unanswered required" in warning for warning in report.warnings))


if __name__ == "__main__":
    unittest.main()
