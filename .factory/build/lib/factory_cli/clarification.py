from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .constants import ARTIFACTS_ROOT
from .project import FactoryError, atomic_write


QUESTION_TYPES = {
    "confirmation",
    "single_choice",
    "multi_choice",
    "free_text",
    "checklist",
}
CLARIFICATION_STATUSES = {"open", "in_progress", "answered", "cancelled"}


@dataclass
class ClarificationQuestion:
    question_id: str
    prompt: str
    question_type: str
    required: bool = True
    context: str = ""
    recommendation: str = ""
    options: List[Dict[str, str]] = field(default_factory=list)
    depends_on: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClarificationQuestion":
        if not isinstance(data, dict):
            raise ValueError("Each clarification question must be a mapping.")
        raw_options = data.get("options", []) or []
        if not isinstance(raw_options, list) or not all(
            isinstance(option, dict) for option in raw_options
        ):
            raise ValueError("Clarification question options must be a list of mappings.")
        dependency = data.get("depends_on")
        if dependency is not None and not isinstance(dependency, dict):
            raise ValueError("Clarification question depends_on must be a mapping or null.")
        question = cls(
            question_id=str(data.get("id", "")),
            prompt=str(data.get("prompt", "")),
            question_type=str(data.get("type", "")),
            required=bool(data.get("required", True)),
            context=str(data.get("context", "")),
            recommendation=str(data.get("recommendation", "")),
            options=[dict(option) for option in raw_options],
            depends_on=dict(dependency) if dependency else None,
        )
        question.validate()
        return question

    def validate(self) -> None:
        if not self.question_id:
            raise ValueError("Clarification question id is required.")
        if not self.prompt:
            raise ValueError(f"Question {self.question_id} requires a prompt.")
        if self.question_type not in QUESTION_TYPES:
            raise ValueError(
                f"Question {self.question_id} has unsupported type: {self.question_type}"
            )
        if self.question_type in {"single_choice", "multi_choice", "checklist"} and not self.options:
            raise ValueError(f"Question {self.question_id} requires options.")
        option_values = []
        for option in self.options:
            value = option.get("value")
            label = option.get("label", value)
            if not isinstance(value, str) or not value:
                raise ValueError(f"Question {self.question_id} has an invalid option value.")
            if not isinstance(label, str) or not label:
                raise ValueError(f"Question {self.question_id} has an invalid option label.")
            option_values.append(value)
        if len(option_values) != len(set(option_values)):
            raise ValueError(f"Question {self.question_id} has duplicate option values.")


@dataclass
class Clarification:
    clarification_id: str
    task_id: str
    status: str
    questions: List[ClarificationQuestion]
    answers: Dict[str, Any] = field(default_factory=dict)
    source_artifacts: List[str] = field(default_factory=list)
    created: str = ""
    updated: str = ""
    answered_at: Optional[str] = None
    body: str = ""
    path: Optional[Path] = None

    def validate(self) -> None:
        if not self.clarification_id:
            raise ValueError("Clarification id is required.")
        if not self.task_id:
            raise ValueError("Clarification task id is required.")
        if self.status not in CLARIFICATION_STATUSES:
            raise ValueError(f"Unsupported clarification status: {self.status}")
        question_ids = {question.question_id for question in self.questions}
        seen = set()
        for question in self.questions:
            question.validate()
            if question.question_id in seen:
                raise ValueError(f"Duplicate clarification question id: {question.question_id}")
            if question.depends_on:
                dependency_id = str(question.depends_on.get("question", ""))
                if dependency_id not in question_ids or dependency_id == question.question_id:
                    raise ValueError(
                        f"Question {question.question_id} has an invalid dependency."
                    )
            seen.add(question.question_id)

    def is_active(self, question: ClarificationQuestion, answers: Optional[Dict[str, Any]] = None) -> bool:
        dependency = question.depends_on
        if not dependency:
            return True
        values = answers if answers is not None else self.answers
        dependency_id = str(dependency.get("question", ""))
        expected = dependency.get("equals")
        actual = values.get(dependency_id)
        if isinstance(actual, list):
            return expected in actual
        return actual == expected

    def missing_required(self, answers: Optional[Dict[str, Any]] = None) -> List[str]:
        values = answers if answers is not None else self.answers
        missing = []
        for question in self.questions:
            if not question.required or not self.is_active(question, values):
                continue
            answer = values.get(question.question_id)
            if answer is None or answer == "" or answer == []:
                missing.append(question.question_id)
        return missing

    def to_frontmatter(self) -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "id": self.clarification_id,
            "task_id": self.task_id,
            "status": self.status,
            "source_artifacts": self.source_artifacts,
            "created": self.created,
            "updated": self.updated,
            "answered_at": self.answered_at,
            "questions": [
                {
                    "id": question.question_id,
                    "type": question.question_type,
                    "prompt": question.prompt,
                    "required": question.required,
                    "context": question.context,
                    "recommendation": question.recommendation,
                    "options": question.options,
                    "depends_on": question.depends_on,
                }
                for question in self.questions
            ],
            "answers": self.answers,
        }


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    if not content.startswith("---\n"):
        raise ValueError("Clarification artifact must start with YAML frontmatter.")
    marker = content.find("\n---\n", 4)
    if marker < 0:
        raise ValueError("Clarification artifact frontmatter is not closed.")
    try:
        data = yaml.safe_load(content[4:marker]) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid clarification YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Clarification frontmatter must be a mapping.")
    return data, content[marker + 5 :]


def load_clarification(path: Path) -> Clarification:
    data, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"Unsupported clarification schema: {data.get('schema_version')}")
    raw_questions = data.get("questions", [])
    raw_answers = data.get("answers", {}) or {}
    raw_sources = data.get("source_artifacts", []) or []
    if not isinstance(raw_questions, list):
        raise ValueError("Clarification questions must be a list.")
    if not isinstance(raw_answers, dict):
        raise ValueError("Clarification answers must be a mapping.")
    if not isinstance(raw_sources, list):
        raise ValueError("Clarification source_artifacts must be a list.")
    clarification = Clarification(
        clarification_id=str(data.get("id", "")),
        task_id=str(data.get("task_id", "")),
        status=str(data.get("status", "open")),
        source_artifacts=[str(item) for item in raw_sources],
        created=str(data.get("created", "")),
        updated=str(data.get("updated", "")),
        answered_at=str(data["answered_at"]) if data.get("answered_at") else None,
        questions=[ClarificationQuestion.from_dict(item) for item in raw_questions],
        answers=dict(raw_answers),
        body=body,
        path=path,
    )
    clarification.validate()
    return clarification


def render_clarification(clarification: Clarification) -> str:
    frontmatter = yaml.safe_dump(
        clarification.to_frontmatter(),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).rstrip()
    body = clarification.body.lstrip("\n") or (
        f"# Clarification: {clarification.task_id}\n\n"
        "Answers are durable owner input. The implementing agent must propagate them into related artifacts.\n"
    )
    return f"---\n{frontmatter}\n---\n{body}"


def save_clarification(
    clarification: Clarification,
    answers: Dict[str, Any],
    submit: bool,
) -> None:
    if not clarification.path:
        raise ValueError("Clarification path is unavailable.")
    clarification.answers = answers
    now = datetime.now(timezone.utc).isoformat()
    clarification.updated = now
    if submit:
        missing = clarification.missing_required(answers)
        if missing:
            raise ValueError(f"Required questions are unanswered: {', '.join(missing)}")
        clarification.status = "answered"
        clarification.answered_at = now
    else:
        clarification.status = "in_progress"
    atomic_write(clarification.path, render_clarification(clarification))


def resolve_clarification(project_dir: Path, identifier: str) -> Path:
    direct = Path(identifier)
    if direct.is_absolute() and direct.is_file():
        return direct
    relative = project_dir / identifier
    if relative.is_file():
        return relative
    artifact_root = project_dir / ARTIFACTS_ROOT
    matches = sorted(artifact_root.glob(f"{identifier}*.md"))
    if not matches:
        raise FactoryError(f"No clarification artifact found for: {identifier}")
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches)
        raise FactoryError(f"Clarification identifier is ambiguous: {names}")
    return matches[0]


def clarification_problems(project_dir: Path) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    artifact_root = project_dir / ARTIFACTS_ROOT
    if not artifact_root.is_dir():
        return errors, warnings
    for path in sorted(artifact_root.glob("CLAR-*.md")):
        try:
            clarification = load_clarification(path)
        except (OSError, ValueError) as exc:
            errors.append(f"invalid clarification {path.name}: {exc}")
            continue
        if clarification.status in {"open", "in_progress"} and clarification.missing_required():
            warnings.append(
                f"clarification {clarification.clarification_id} has unanswered required questions"
            )
    return errors, warnings
