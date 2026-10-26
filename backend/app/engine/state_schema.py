"""JSON Schema of a workflow's state fields: the input/state schema of `/api/lg` assistants and of the MCP tool (TASK-0114)."""
from typing import Any, Dict

JSON_TYPES = {"string": "string", "number": "number", "integer": "integer", "boolean": "boolean", "object": "object", "list": "array"}


def state_schema(wf: Dict[str, Any], title: str = "State") -> dict:
    props = {f["name"]: {"type": JSON_TYPES.get(f.get("type"), "string"), **({"description": f["description"]} if f.get("description") else {})}
             for f in wf.get("state") or [] if f.get("name")}
    return {"title": title, "type": "object", "properties": props}
