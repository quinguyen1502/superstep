from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from abc import abstractmethod
from pathlib import Path
from typing import List, Optional

from .adapters import ScaffoldAdapter
from .models import AdapterPreview, ScaffoldTarget


GENERATOR_TIMEOUT_SECONDS = 300


class CommandScaffoldAdapter(ScaffoldAdapter):
    """Base for reviewed, non-interactive wrappers around official generators."""

    executable_name: str
    expected_paths: List[str]
    install_hint = "Install the provider CLI and ensure it is available on PATH."

    def detect(self) -> Optional[str]:
        return shutil.which(self.executable_name)

    @abstractmethod
    def build_command(self, executable: str, targets: List[ScaffoldTarget]) -> List[str]:
        """Build a command that runs with the staging directory as cwd."""

    def preview(self, targets: List[ScaffoldTarget]) -> AdapterPreview:
        executable = self.detect()
        return AdapterPreview(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            targets=list(targets),
            available=executable is not None,
            command=self.build_command(executable or self.executable_name, targets),
            expected_paths=list(self.expected_paths),
            reason=(
                ""
                if executable is not None
                else f"{self.executable_name} was not found on PATH. {self.install_hint}"
            ),
        )

    def prepare(self, targets: List[ScaffoldTarget], staging_dir: Path) -> None:
        """Create destination directories required by a provider CLI."""

    def execute(self, targets: List[ScaffoldTarget], staging_dir: Path) -> None:
        executable = self.detect()
        if executable is None:
            raise RuntimeError(f"{self.executable_name} was not found on PATH")
        self.prepare(targets, staging_dir)
        command = self.build_command(executable, targets)
        environment = os.environ.copy()
        environment.update(
            {
                "CI": "1",
                "NO_COLOR": "1",
                "npm_config_yes": "true",
            }
        )
        try:
            completed = subprocess.run(
                command,
                cwd=staging_dir,
                env=environment,
                text=True,
                capture_output=True,
                timeout=GENERATOR_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"generator timed out after {GENERATOR_TIMEOUT_SECONDS} seconds"
            ) from exc
        except OSError as exc:
            raise RuntimeError(f"generator could not start: {exc}") from exc
        if completed.returncode:
            detail = (completed.stderr or completed.stdout or "unknown error").strip()
            if len(detail) > 2000:
                detail = detail[-2000:]
            raise RuntimeError(
                f"generator exited with status {completed.returncode}: {detail}"
            )


class ViteAdapter(CommandScaffoldAdapter):
    adapter_id = "vite"
    executable_name = "npm"
    install_hint = "Install a supported Node.js release, which includes npm."
    expected_paths = ["frontend/package.json", "frontend/src"]
    templates = {
        "React + TypeScript": "react-ts",
        "Vue + TypeScript": "vue-ts",
    }

    def supports(self, target: ScaffoldTarget) -> bool:
        return target.area == "frontend" and target.technology in self.templates

    def build_command(self, executable: str, targets: List[ScaffoldTarget]) -> List[str]:
        template = self.templates[targets[0].technology]
        return [
            executable,
            "create",
            "vite@latest",
            "frontend",
            "--",
            "--template",
            template,
            "--no-interactive",
        ]


class NextJsAdapter(CommandScaffoldAdapter):
    adapter_id = "nextjs"
    executable_name = "npx"
    install_hint = "Install a supported Node.js release, which includes npx."
    expected_paths = ["frontend/package.json", "frontend/src/app"]

    def supports(self, target: ScaffoldTarget) -> bool:
        return target.area == "frontend" and target.technology == "Next.js"

    def build_command(self, executable: str, targets: List[ScaffoldTarget]) -> List[str]:
        return [
            executable,
            "create-next-app@latest",
            "frontend",
            "--ts",
            "--eslint",
            "--app",
            "--src-dir",
            "--use-npm",
            "--skip-install",
            "--disable-git",
            "--yes",
        ]


class SvelteKitAdapter(CommandScaffoldAdapter):
    adapter_id = "sveltekit"
    executable_name = "npx"
    install_hint = "Install a supported Node.js release, which includes npx."
    expected_paths = ["frontend/package.json", "frontend/src/routes"]

    def supports(self, target: ScaffoldTarget) -> bool:
        return target.area == "frontend" and target.technology == "SvelteKit"

    def build_command(self, executable: str, targets: List[ScaffoldTarget]) -> List[str]:
        return [
            executable,
            "sv",
            "create",
            "frontend",
            "--template",
            "minimal",
            "--types",
            "ts",
            "--no-add-ons",
            "--no-install",
        ]


class AngularAdapter(CommandScaffoldAdapter):
    adapter_id = "angular"
    executable_name = "npx"
    install_hint = "Install a supported Node.js release, which includes npx."
    expected_paths = [
        "frontend/package.json",
        "frontend/angular.json",
        "frontend/src",
    ]

    def supports(self, target: ScaffoldTarget) -> bool:
        return target.area == "frontend" and target.technology == "Angular + TypeScript"

    def build_command(self, executable: str, targets: List[ScaffoldTarget]) -> List[str]:
        return [
            executable,
            "@angular/cli@latest",
            "new",
            "frontend",
            "--defaults",
            "--routing",
            "--style=scss",
            "--strict",
            "--test-runner=vitest",
            "--skip-git",
            "--skip-install",
            "--package-manager=npm",
        ]


class DjangoAdapter(CommandScaffoldAdapter):
    adapter_id = "django"
    adapter_version = 2
    executable_name = "django-admin"
    install_hint = (
        "Activate a project virtual environment and install Django there; "
        "do not install it into externally managed system Python."
    )
    expected_paths = [
        "backend/manage.py",
        "backend/config/settings.py",
        "backend/pyproject.toml",
        "backend/.gitignore",
    ]

    def supports(self, target: ScaffoldTarget) -> bool:
        return target.area == "backend" and target.technology == "Python + Django"

    def detect(self) -> Optional[str]:
        executable = super().detect()
        if executable is not None:
            return executable
        if importlib.util.find_spec("django") is not None:
            return sys.executable
        return None

    def prepare(self, targets: List[ScaffoldTarget], staging_dir: Path) -> None:
        (staging_dir / "backend").mkdir()

    def build_command(self, executable: str, targets: List[ScaffoldTarget]) -> List[str]:
        command = [executable]
        if Path(executable).resolve() == Path(sys.executable).resolve():
            command.extend(["-m", "django"])
        return command + ["startproject", "config", "backend"]

    def execute(self, targets: List[ScaffoldTarget], staging_dir: Path) -> None:
        super().execute(targets, staging_dir)
        (staging_dir / "backend" / "pyproject.toml").write_text(
            """[project]
name = "backend"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = ["Django"]
""",
            encoding="utf-8",
        )
        (staging_dir / "backend" / ".gitignore").write_text(
            ".venv/\n__pycache__/\n*.py[cod]\n.pytest_cache/\n",
            encoding="utf-8",
        )


class FastApiTemplateAdapter(ScaffoldAdapter):
    """Maintained baseline for FastAPI, which has no official project generator."""

    adapter_id = "fastapi-template"
    adapter_version = 2
    expected_paths = [
        "backend/pyproject.toml",
        "backend/.gitignore",
        "backend/app/main.py",
        "backend/tests/test_health.py",
    ]

    def supports(self, target: ScaffoldTarget) -> bool:
        return (
            target.area == "backend"
            and target.technology == "Python + FastAPI + REST"
        )

    def preview(self, targets: List[ScaffoldTarget]) -> AdapterPreview:
        return AdapterPreview(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            targets=list(targets),
            available=True,
            expected_paths=list(self.expected_paths),
            reason="Factory-maintained deterministic baseline; FastAPI has no project CLI",
        )

    def execute(self, targets: List[ScaffoldTarget], staging_dir: Path) -> None:
        files = {
            "backend/.gitignore": ".venv/\n__pycache__/\n*.py[cod]\n.pytest_cache/\n",
            "backend/pyproject.toml": """[project]
name = "backend"
version = "0.1.0"
requires-python = ">=3.9"
dependencies = ["fastapi", "uvicorn[standard]"]

[project.optional-dependencies]
test = ["httpx", "pytest"]

[tool.pytest.ini_options]
pythonpath = ["."]
""",
            "backend/app/__init__.py": "",
            "backend/app/main.py": """from fastapi import FastAPI


app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
""",
            "backend/tests/test_health.py": """from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
""",
        }
        for relative_path, content in files.items():
            destination = staging_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")


class PythonCliTemplateAdapter(ScaffoldAdapter):
    adapter_id = "python-cli-template"
    adapter_version = 2
    expected_paths = [
        "backend/pyproject.toml",
        "backend/.gitignore",
        "backend/app/__main__.py",
        "backend/tests/test_cli.py",
    ]

    def supports(self, target: ScaffoldTarget) -> bool:
        return target.area == "backend" and target.technology == "Python CLI"

    def preview(self, targets: List[ScaffoldTarget]) -> AdapterPreview:
        return AdapterPreview(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            targets=list(targets),
            available=True,
            expected_paths=list(self.expected_paths),
            reason="Factory-maintained deterministic Python CLI baseline",
        )

    def execute(self, targets: List[ScaffoldTarget], staging_dir: Path) -> None:
        files = {
            "backend/.gitignore": ".venv/\n__pycache__/\n*.py[cod]\n.pytest_cache/\n",
            "backend/pyproject.toml": """[project]
name = "app"
version = "0.1.0"
requires-python = ">=3.9"

[project.optional-dependencies]
test = ["pytest"]

[project.scripts]
app = "app.__main__:main"
""",
            "backend/app/__init__.py": "",
            "backend/app/__main__.py": """def main() -> None:
    print("Hello from app")


if __name__ == "__main__":
    main()
""",
            "backend/tests/test_cli.py": """from app.__main__ import main


def test_main(capsys) -> None:
    main()
    assert capsys.readouterr().out == "Hello from app\\n"
""",
        }
        for relative_path, content in files.items():
            destination = staging_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")


class NestJsAdapter(CommandScaffoldAdapter):
    adapter_id = "nestjs"
    executable_name = "npx"
    install_hint = "Install a supported Node.js release, which includes npx."
    expected_paths = ["backend/package.json", "backend/src/main.ts"]

    def supports(self, target: ScaffoldTarget) -> bool:
        return target.area == "backend" and target.technology == "Node.js + NestJS"

    def build_command(self, executable: str, targets: List[ScaffoldTarget]) -> List[str]:
        return [
            executable,
            "@nestjs/cli@latest",
            "new",
            "backend",
            "--language",
            "TS",
            "--package-manager",
            "npm",
            "--skip-install",
            "--skip-git",
        ]


class FlutterAdapter(CommandScaffoldAdapter):
    adapter_id = "flutter"
    executable_name = "flutter"
    install_hint = "Install the Flutter SDK and add its bin directory to PATH."
    expected_paths = ["mobile/pubspec.yaml", "mobile/lib/main.dart"]

    def supports(self, target: ScaffoldTarget) -> bool:
        return target.area == "mobile" and target.technology == "Flutter"

    def build_command(self, executable: str, targets: List[ScaffoldTarget]) -> List[str]:
        return [executable, "create", "--no-pub", "mobile"]


class SpringBootAdapter(CommandScaffoldAdapter):
    adapter_id = "spring-boot"
    executable_name = "spring"
    install_hint = "Install a Java runtime and the Spring Boot CLI."
    expected_paths = [
        "backend/pom.xml",
        "backend/mvnw",
        "backend/src/main",
        "backend/src/test",
    ]

    def supports(self, target: ScaffoldTarget) -> bool:
        return target.area == "backend" and target.technology == "Java + Spring Boot"

    def build_command(self, executable: str, targets: List[ScaffoldTarget]) -> List[str]:
        return [
            executable,
            "init",
            "--build=maven",
            "--language=java",
            "--dependencies=web,validation",
            "--packaging=jar",
            "--extract",
            "backend",
        ]


class AspNetCoreAdapter(CommandScaffoldAdapter):
    adapter_id = "aspnet-core"
    executable_name = "dotnet"
    install_hint = "Install a supported .NET SDK."
    expected_paths = [
        "backend/backend.csproj",
        "backend/Program.cs",
        "backend/appsettings.json",
    ]

    def supports(self, target: ScaffoldTarget) -> bool:
        return target.area == "backend" and target.technology == "ASP.NET Core Web API"

    def build_command(self, executable: str, targets: List[ScaffoldTarget]) -> List[str]:
        return [
            executable,
            "new",
            "webapi",
            "--output",
            "backend",
            "--no-restore",
            "--no-update-check",
        ]


class GoGinTemplateAdapter(ScaffoldAdapter):
    adapter_id = "go-gin-template"
    expected_paths = [
        "backend/go.mod",
        "backend/main.go",
        "backend/main_test.go",
        "backend/.gitignore",
    ]

    def supports(self, target: ScaffoldTarget) -> bool:
        return target.area == "backend" and target.technology in {
            "Go + Gin REST",
            "Go + REST",
        }

    def preview(self, targets: List[ScaffoldTarget]) -> AdapterPreview:
        return AdapterPreview(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            targets=list(targets),
            available=True,
            expected_paths=list(self.expected_paths),
            reason="Factory-maintained Gin REST baseline; dependency apply requires Go 1.25+",
        )

    def execute(self, targets: List[ScaffoldTarget], staging_dir: Path) -> None:
        files = {
            "backend/.gitignore": "bin/\n",
            "backend/go.mod": """module backend

go 1.25.0

require github.com/gin-gonic/gin v1.12.0
""",
            "backend/main.go": """package main

import (
    "net/http"

    "github.com/gin-gonic/gin"
)

func router() *gin.Engine {
    engine := gin.New()
    engine.Use(gin.Recovery())
    engine.GET("/health", func(context *gin.Context) {
        context.JSON(http.StatusOK, gin.H{"status": "ok"})
    })
    return engine
}

func main() {
    if err := router().Run(); err != nil {
        panic(err)
    }
}
""",
            "backend/main_test.go": """package main

import (
    "net/http"
    "net/http/httptest"
    "testing"
)

func TestHealth(t *testing.T) {
    response := httptest.NewRecorder()
    request := httptest.NewRequest(http.MethodGet, "/health", nil)
    router().ServeHTTP(response, request)
    if response.Code != http.StatusOK {
        t.Fatalf("expected status %d, received %d", http.StatusOK, response.Code)
    }
}
""",
        }
        for relative_path, content in files.items():
            destination = staging_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")


def builtin_scaffold_adapters() -> List[ScaffoldAdapter]:
    return [
        ViteAdapter(),
        NextJsAdapter(),
        SvelteKitAdapter(),
        AngularAdapter(),
        DjangoAdapter(),
        FastApiTemplateAdapter(),
        PythonCliTemplateAdapter(),
        NestJsAdapter(),
        FlutterAdapter(),
        SpringBootAdapter(),
        AspNetCoreAdapter(),
        GoGinTemplateAdapter(),
    ]
