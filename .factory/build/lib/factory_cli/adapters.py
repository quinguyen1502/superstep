from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Dict, List, Optional, Type

from .models import RefinementResult


class AdapterError(Exception):
    """Raised when an AI coding tool cannot produce a valid refinement."""


ProgressCallback = Callable[[str], None]


REFINEMENT_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "markdown": {"type": "string"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["markdown", "assumptions", "open_questions"],
    "additionalProperties": False,
}


class ToolAdapter(ABC):
    tool_id: str
    executable: str

    def detect(self) -> Optional[str]:
        return shutil.which(self.executable)

    def instruction_assets(self) -> Dict[str, str]:
        """Return provider-specific bridges beyond canonical AGENTS.md."""
        return {}

    @abstractmethod
    def command(
        self,
        executable: str,
        prompt: str,
        output_path: Optional[Path] = None,
        schema_path: Optional[Path] = None,
    ) -> List[str]:
        raise NotImplementedError

    def launch_command(self, executable: str, brief_path: Path) -> List[str]:
        """Return argv to start a human-supervised working session.

        Unlike ``command``/``refine`` this is not read-only: the session is meant
        to be driven by a person in an isolated worktree, and write permissions
        are governed by the provider's own policy (the project tool kit), not by
        Factory. The caller runs this with ``cwd`` set to the task worktree.
        """
        return [executable]

    def progress_from_output(self, line: str) -> Optional[str]:
        return None

    def refine(
        self,
        intake_yaml: str,
        template: str,
        timeout: int = 300,
        progress: Optional[ProgressCallback] = None,
        cancel_event: Optional[threading.Event] = None,
        sections: Optional[List[str]] = None,
    ) -> RefinementResult:
        executable = self.detect()
        if not executable:
            raise AdapterError(f"{self.tool_id} CLI is not installed or not on PATH.")

        section_instruction = (
            " Refine only these level-two sections and preserve every other section "
            f"verbatim: {', '.join(sections)}."
            if sections
            else " Refine the entire specification."
        )
        prompt = (
            "Refine the project specification using only intake.yaml and template.md in the "
            "current directory. Preserve explicit statuses and never turn Preferred, Proposed, "
            "or Unknown items into Approved decisions. Return JSON only with keys markdown, "
            "assumptions, and open_questions. Do not edit files."
            + section_instruction
        )
        try:
            with tempfile.TemporaryDirectory(prefix="factory-refine-") as temp_dir:
                workdir = Path(temp_dir)
                (workdir / "intake.yaml").write_text(intake_yaml, encoding="utf-8")
                (workdir / "template.md").write_text(template, encoding="utf-8")
                output_path = workdir / "refinement-output.json"
                schema_path = workdir / "refinement-schema.json"
                schema_path.write_text(
                    json.dumps(REFINEMENT_OUTPUT_SCHEMA), encoding="utf-8"
                )
                self.emit(progress, f"Starting {self.tool_id} CLI…")
                process = subprocess.Popen(
                    self.command(executable, prompt, output_path, schema_path),
                    cwd=workdir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
                stdout_lines: List[str] = []
                stderr_lines: List[str] = []
                readers = [
                    threading.Thread(
                        target=self.read_stream,
                        args=(process.stdout, stdout_lines, progress, True),
                        daemon=True,
                    ),
                    threading.Thread(
                        target=self.read_stream,
                        args=(process.stderr, stderr_lines, progress, False),
                        daemon=True,
                    ),
                ]
                for reader in readers:
                    reader.start()

                deadline = time.monotonic() + timeout
                while process.poll() is None:
                    if cancel_event is not None and cancel_event.is_set():
                        self.stop_process(process)
                        raise AdapterError(f"{self.tool_id} refinement was cancelled.")
                    if time.monotonic() >= deadline:
                        self.stop_process(process)
                        raise AdapterError(
                            f"{self.tool_id} refinement timed out after {timeout}s."
                        )
                    time.sleep(0.05)

                for reader in readers:
                    reader.join(timeout=0.5)
                stdout = "".join(stdout_lines)
                stderr = "".join(stderr_lines)
                if process.returncode != 0:
                    detail = stderr.strip() or stdout.strip() or "unknown error"
                    raise AdapterError(f"{self.tool_id} refinement failed: {detail}")
                self.emit(progress, f"Validating {self.tool_id} output…")
                output = (
                    output_path.read_text(encoding="utf-8")
                    if output_path.is_file()
                    else stdout
                )
        except OSError as exc:
            raise AdapterError(f"Unable to run {self.tool_id}: {exc}") from exc
        return normalize_output(output)

    def read_stream(
        self,
        stream,
        sink: List[str],
        progress: Optional[ProgressCallback],
        parse_progress: bool,
    ) -> None:
        if stream is None:
            return
        for line in iter(stream.readline, ""):
            sink.append(line)
            if parse_progress:
                message = self.progress_from_output(line)
                if message:
                    self.emit(progress, message)
        stream.close()

    @staticmethod
    def emit(progress: Optional[ProgressCallback], message: str) -> None:
        if progress is not None:
            progress(message)

    @staticmethod
    def stop_process(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)


class CodexAdapter(ToolAdapter):
    tool_id = "codex"
    executable = "codex"

    def command(
        self,
        executable: str,
        prompt: str,
        output_path: Optional[Path] = None,
        schema_path: Optional[Path] = None,
    ) -> List[str]:
        command = [
            executable,
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--json",
        ]
        if schema_path is not None:
            command.extend(("--output-schema", str(schema_path)))
        if output_path is not None:
            command.extend(("--output-last-message", str(output_path)))
        command.append(prompt)
        return command

    def progress_from_output(self, line: str) -> Optional[str]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return None
        event_type = str(event.get("type", ""))
        direct_messages = {
            "thread.started": "Codex session started…",
            "turn.started": "Codex is analyzing the project context…",
            "turn.completed": "Codex finished generating the specification…",
        }
        if event_type in direct_messages:
            return direct_messages[event_type]
        if event_type in {"item.started", "item.completed"}:
            item = event.get("item") or {}
            item_type = str(item.get("type", ""))
            item_messages = {
                "reasoning": "Codex is reasoning about scope and constraints…",
                "agent_message": "Codex is drafting the refined specification…",
                "command_execution": "Codex is inspecting staged inputs…",
            }
            return item_messages.get(item_type)
        return None


class CursorAdapter(ToolAdapter):
    tool_id = "cursor"
    executable = "cursor-agent"

    def command(
        self,
        executable: str,
        prompt: str,
        output_path: Optional[Path] = None,
        schema_path: Optional[Path] = None,
    ) -> List[str]:
        return [executable, "-p", prompt, "--output-format", "json"]


class ClaudeCodeAdapter(ToolAdapter):
    tool_id = "claude-code"
    executable = "claude"

    def instruction_assets(self) -> Dict[str, str]:
        return {
            ".claude/CLAUDE.md": "# Claude Code Project Instructions\n\n@../AGENTS.md\n"
        }

    def command(
        self,
        executable: str,
        prompt: str,
        output_path: Optional[Path] = None,
        schema_path: Optional[Path] = None,
    ) -> List[str]:
        return [
            executable,
            "-p",
            "--permission-mode",
            "plan",
            "--tools",
            "Read",
            "--output-format",
            "json",
            prompt,
        ]


class GrokAdapter(ToolAdapter):
    tool_id = "grok"
    executable = "grok"

    def command(
        self,
        executable: str,
        prompt: str,
        output_path: Optional[Path] = None,
        schema_path: Optional[Path] = None,
    ) -> List[str]:
        command = [
            executable,
            "--single",
            prompt,
            "--output-format",
            "json",
            "--permission-mode",
            "plan",
            "--sandbox",
            "read-only",
            "--tools",
            "read_file,grep,list_dir",
        ]
        if schema_path is not None:
            command.extend(("--json-schema", schema_path.read_text(encoding="utf-8")))
        return command


ADAPTER_TYPES: Dict[str, Type[ToolAdapter]] = {
    "codex": CodexAdapter,
    "cursor": CursorAdapter,
    "claude-code": ClaudeCodeAdapter,
    "grok": GrokAdapter,
}


def get_adapter(tool_id: str) -> ToolAdapter:
    try:
        return ADAPTER_TYPES[tool_id]()
    except KeyError as exc:
        raise AdapterError(f"Unsupported AI tool: {tool_id}") from exc


def detect_tools() -> Dict[str, bool]:
    return {tool_id: adapter_type().detect() is not None for tool_id, adapter_type in ADAPTER_TYPES.items()}


def normalize_output(output: str) -> RefinementResult:
    text = output.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AdapterError("AI refinement did not return valid JSON.") from exc

    if isinstance(data, dict) and isinstance(data.get("result"), str):
        result_text = data["result"].strip()
        try:
            data = json.loads(result_text)
        except json.JSONDecodeError:
            data = {"markdown": result_text, "assumptions": [], "open_questions": []}

    if not isinstance(data, dict) or not isinstance(data.get("markdown"), str):
        raise AdapterError("AI refinement JSON must contain a markdown string.")
    assumptions = data.get("assumptions", [])
    open_questions = data.get("open_questions", [])
    if not isinstance(assumptions, list) or not isinstance(open_questions, list):
        raise AdapterError("AI refinement assumptions and open_questions must be arrays.")
    markdown = data["markdown"].strip()
    if not markdown.startswith("# Project Specs"):
        raise AdapterError("AI refinement must start with '# Project Specs'.")
    return RefinementResult(
        markdown=markdown + "\n",
        assumptions=[str(value) for value in assumptions],
        open_questions=[str(value) for value in open_questions],
    )
