"""Static Dataset bindings and the typed inputs rendered by the engine."""
from __future__ import annotations

import re

from .issues import Issue

SCOPE = "_dataset_workflow"
DRY_RUN = "_dataset_dry_run"
ACCESS = {"find_rows": "read", "get_row": "read", "insert_row": "write", "upsert_row": "write"}
INPUTS = {
    "find_rows": {"filters", "filter_mode", "search", "sorts", "limit", "offset"},
    "get_row": {"row_id"},
    "insert_row": {"values"},
    "upsert_row": {"values", "key"},
}
KEY = re.compile(r"[a-z][a-z0-9_]{0,62}")


def _key(value) -> bool:
    return isinstance(value, str) and KEY.fullmatch(value) is not None


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
    else:
        values = args.get("values")
        if not isinstance(values, dict) or len(values) > 100 or not all(_key(field) for field in values):
            return False
        if operation == "upsert_row":
            return _key(args.get("key")) and args["key"] in values
    return True


def errors(node_id: str, data: dict) -> list:
    return [] if valid(data) else [Issue("DATASET_NODE_BINDING", node=node_id)]


def bindings(workflow: dict | None) -> dict:
    nodes = (workflow or {}).get("nodes")
    if not isinstance(nodes, list):
        return {}
    return {
        node["id"]: {key: data.get(key) for key in ("dataset_id", "operation", "fields", "arguments", "output_field") if key in data}
        for node in nodes
        if isinstance(node, dict) and node.get("type") == "dataset" and isinstance(node.get("id"), str)
        for data in [node.get("data") or {}] if isinstance(data, dict)
    }


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
