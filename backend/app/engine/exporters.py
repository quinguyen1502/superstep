"""The workflow-to-code exporters: one entry per language, all with the same signature
`(wf, name, version, children, example) -> Export`. The service and the API pick one by `language`."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict
from .export_common import Export
from .python_export import to_python
from .typescript_export import to_typescript


@dataclass(frozen=True)
class Exporter:
    id: str
    label: str
    media_type: str
    write: Callable[..., Export]


EXPORTERS: Dict[str, Exporter] = {
    "python": Exporter("python", "Python (LangGraph)", "text/x-python", to_python),
    "typescript": Exporter("typescript", "TypeScript (LangGraph.js)", "text/typescript", to_typescript),
}
DEFAULT = "python"
