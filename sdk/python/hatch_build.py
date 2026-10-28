"""Copy the repo CHANGELOG into the sdist, then into the wheel.

`python -m build` builds the wheel from the sdist. A force-include path that
points outside `sdk/python` is gone by then, so the sdist has to carry the file.
"""
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        root = Path(self.root).resolve()
        repo_log = root.parent.parent / "CHANGELOG.md"
        bundled = root / "src" / "superstep" / "cli" / "CHANGELOG.md"
        if self.target_name == "wheel":
            source = bundled if bundled.is_file() else repo_log
            destination = "superstep/cli/CHANGELOG.md"
        else:
            source = repo_log if repo_log.is_file() else bundled
            destination = "src/superstep/cli/CHANGELOG.md"
        if not source.is_file():
            raise FileNotFoundError(f"CHANGELOG.md was not found at {repo_log} or {bundled}")
        build_data["force_include"][str(source)] = destination
