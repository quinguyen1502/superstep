"""Static Dataset bindings and the typed inputs rendered by the engine."""
from __future__ import annotations

import re

from ..core.dataset_types import FILTER_OPERATORS
from ..core.errors import AppError
from .issues import Issue

SCOPE = "_dataset_workflow"
DRY_RUN = "_dataset_dry_run"
ACCESS = {"find_rows": "read", "get_row": "read", "insert_row": "write", "upsert_row": "write", "delete_row": "delete"}
INPUTS = {
    "find_rows": {"filters", "filter_mode", "search", "sorts", "limit", "offset"},
    "get_row": {"row_id"},
    "insert_row": {"values"},
    "upsert_row": {"values", "key"},
    "delete_row": {"row_id", "key", "value"},
}
AGENT_MAX_ROWS = 20
AGENT_MAX_FILTERS = 12
KEY = re.compile(r"[a-z][a-z0-9_]{0,62}")


def _key(value) -> bool:
    return isinstance(value, str) and KEY.fullmatch(value) is not None


def _valid_delete(args: dict) -> bool:
    has_id, has_key = "row_id" in args, "key" in args or "value" in args
    if has_id == has_key or (has_key and ("key" not in args or "value" not in args)):
        return False
    if has_id:
        row_id = args["row_id"]
        return isinstance(row_id, str) and 0 < len(row_id) <= 100
    value = args["value"]
    return _key(args.get("key")) and value is not None and not isinstance(value, (dict, list))


def delete_target(arguments: dict) -> tuple[str | None, str | None, object]:
    """Return a row id, or a unique column and its value. The two forms are exclusive."""
    if not isinstance(arguments, dict) or not _valid_delete(arguments):
        raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
    if "row_id" in arguments:
        return arguments["row_id"], None, None
    return None, arguments["key"], arguments["value"]


def valid(data: dict) -> bool:
    if not isinstance(data, dict):
        return False
    operation = data.get("operation")
    if not isinstance(operation, str) or operation not in ACCESS:
        return False
    dataset_id, fields, args = data.get("dataset_id"), data.get("fields"), data.get("arguments", {})
    if (not isinstance(dataset_id, str) or not 0 < len(dataset_id) <= 100
            or not isinstance(fields, list) or not 0 < len(fields) <= 100
            or not all(_key(field) for field in fields) or len(set(fields)) != len(fields)
            or not isinstance(args, dict) or set(args) - INPUTS[operation]):
        return False
    if operation == "find_rows":
        for name in ("filters", "sorts"):
            rules = args.get(name, [])
            if not isinstance(rules, list) or len(rules) > 12:
                return False
            if any(not isinstance(rule, dict) or not _key(rule.get("field")) for rule in rules):
                return False
    elif operation == "get_row":
        return isinstance(args.get("row_id"), str) and bool(args["row_id"])
    elif operation == "delete_row":
        return _valid_delete(args)
    else:
        values = args.get("values")
        if not isinstance(values, dict) or len(values) > 100 or not all(_key(field) for field in values):
            return False
        if operation == "upsert_row":
            return _key(args.get("key")) and args["key"] in values
    return True


def errors(node_id: str, data: dict) -> list:
    return [] if valid(data) else [Issue("DATASET_NODE_BINDING", node=node_id)]


def agent_binding(tool: dict) -> dict:
    return {
        "dataset_id": tool.get("dataset_id"), "operation": "find_rows", "fields": tool.get("fields"),
        "arguments": {"limit": tool.get("limit", 10)}, "filter_ops": tool.get("filter_ops", {}),
    }


def valid_agent(binding: dict) -> bool:
    if not valid(binding):
        return False
    limit, allowed = binding["arguments"]["limit"], binding["filter_ops"]
    return (
        type(limit) is int and 1 <= limit <= AGENT_MAX_ROWS
        and isinstance(allowed, dict) and len(allowed) <= 100
        and all(_key(field) and isinstance(ops, list) and 0 < len(ops) <= len(FILTER_OPERATORS)
                and all(op in FILTER_OPERATORS for op in ops) and len(set(ops)) == len(ops)
                for field, ops in allowed.items())
    )


def agent_parameters(tool: dict) -> dict:
    binding = agent_binding(tool)
    allowed = binding["filter_ops"] if valid_agent(binding) else {}
    properties = {}
    if allowed:
        policies = ", ".join(f"{field}: {'/'.join(ops)}" for field, ops in allowed.items())
        properties["filters"] = {
            "type": "array", "maxItems": AGENT_MAX_FILTERS, "description": f"Match every filter. Allowed operators by field: {policies}.",
            "items": {"type": "object", "additionalProperties": False, "required": ["field", "op"], "properties": {
                "field": {"type": "string", "enum": list(allowed)},
                "op": {"type": "string", "enum": sorted({op for ops in allowed.values() for op in ops}),
                       "description": "eq matches the exact value, letter case included. ne also matches empty cells. "
                                      "contains ignores letter case. is_null matches empty cells and not_null filled ones."},
                "value": {"description": "A string, number or boolean matching the field type. Omit for is_null and not_null.",
                          "type": ["string", "number", "boolean", "null"]},
            }},
        }
    return {"type": "object", "properties": properties, "additionalProperties": False}


def agent_query(tool: dict, args: dict, scope: str | None) -> tuple[dict, dict]:
    binding = agent_binding(tool)
    if not valid_agent(binding) or not isinstance(args, dict) or set(args) - {"filters"}:
        raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
    filters = args.get("filters", [])
    if not isinstance(filters, list) or len(filters) > AGENT_MAX_FILTERS:
        raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
    allowed = binding["filter_ops"]
    for rule in filters:
        if not isinstance(rule, dict) or not _key(rule.get("field")):
            raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
        if rule.get("op") not in allowed.get(rule["field"], []):
            raise AppError("DATASET_FILTER_INVALID", field=rule["field"])
    return {**binding, SCOPE: scope}, {**binding["arguments"], "filters": filters}


def bindings(workflow: dict | None) -> dict:
    nodes = (workflow or {}).get("nodes")
    if not isinstance(nodes, list):
        return {}
    result = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not isinstance(node.get("data"), dict):
            continue
        node_id, data = node["id"], node["data"]
        if node.get("type") == "dataset":
            result[node_id] = {key: data[key] for key in ("dataset_id", "operation", "fields", "arguments", "output_field") if key in data}
        if node.get("type") in {"agent", "agent_tool"} and isinstance(data.get("tools"), list):
            for index, tool in enumerate(data["tools"]):
                if isinstance(tool, dict) and tool.get("source") == "dataset":
                    result[node_id, index] = agent_binding(tool)
    return result


def strip_runtime_scope(workflow: dict) -> dict:
    """Scope and dry-run markers come only from trusted expansion and run plans."""
    result = {key: value for key, value in workflow.items() if key != DRY_RUN}
    if isinstance(result.get("nodes"), list):
        result["nodes"] = [
            {**node, "data": {key: value for key, value in node["data"].items() if key != SCOPE}}
            if isinstance(node, dict) and isinstance(node.get("data"), dict) and SCOPE in node["data"] else node
            for node in result["nodes"]
        ]
    return result
