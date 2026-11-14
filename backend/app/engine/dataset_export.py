"""Build a deployment contract without publishing Studio resource identifiers."""
from dataclasses import dataclass
from typing import Callable, Iterable

from ..core.dataset_filters import LIST_FILTERS
from ..core.errors import AppError
from . import dataset_nodes


@dataclass
class DatasetExport:
    aliases: dict[str, str]
    bindings: dict[str, dict]

    def manifest(self) -> dict:
        return {"format": "superstep/dataset-bindings", "version": 1, "bindings": list(self.bindings.values())}


def prepare(graphs: Iterable[dict], schema: Callable[[str], list[dict]]) -> DatasetExport:
    out = DatasetExport({}, {})
    for graph in graphs:
        for binding in dataset_nodes.bindings(graph).values():
            did, operation = binding.get("dataset_id"), binding.get("operation")
            if not (dataset_nodes.valid_agent(binding) if "filter_ops" in binding else dataset_nodes.valid(binding)):
                raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
            alias = out.aliases.get(did)
            if alias is None:
                alias = f"DATASET_{len(out.aliases) + 1}"
                out.aliases[did] = alias
                columns = [{key: value for key, value in column.items() if key not in {"label", "display_format"}} for column in schema(did)]
                out.bindings[alias] = {"name": alias, "columns": columns, "operations": []}
            contract = out.bindings[alias]
            columns = {column["key"]: column for column in contract["columns"]}
            args = binding.get("arguments") or {}
            if operation == "aggregate_rows" or "aggregate_rows" in binding.get("operations", []):
                raise AppError("DATASET_EXPORT_AGGREGATE_UNSUPPORTED")
            new_operators = LIST_FILTERS | {"not_contains"}
            if (args.get("filter_tree") is not None
                    or any(rule.get("op") in new_operators for rule in args.get("filters", []))
                    or any(new_operators.intersection(ops) for ops in binding.get("filter_ops", {}).values())):
                raise AppError("DATASET_EXPORT_FILTER_UNSUPPORTED")
            referenced = {*binding["fields"], *(args.get("values") or {}), *binding.get("filter_ops", {})}
            referenced.update(rule["field"] for name in ("filters", "sorts") for rule in args.get(name, []))
            if operation == "delete_row" and "key" in args:
                referenced.add(args["key"])
            agent_writes = dataset_nodes.agent_writes(binding) if "filter_ops" in binding else []
            if agent_writes:
                referenced.update(binding["write_fields"])
            if absent := sorted(referenced - columns.keys()):
                raise AppError("DATASET_BINDING_SCHEMA_MISMATCH", field=absent[0])
            if any(column.get("validation_rules") for column in columns.values()):
                raise AppError("DATASET_EXPORT_COLUMN_KIND_UNSUPPORTED")
            unsupported = {"long_text", "url", "created_time", "updated_time", "multi_select", "auto_number"}
            if unsupported.intersection(column["kind"] for column in columns.values()):
                raise AppError("DATASET_EXPORT_COLUMN_KIND_UNSUPPORTED")
            if operation in {"upsert_row", "delete_row"} and "key" in args and not columns[args["key"]]["unique"]:
                raise AppError("DATASET_UPSERT_KEY_INVALID", field=args["key"])
            if "upsert_row" in agent_writes and not columns[binding["key"]]["unique"]:
                raise AppError("DATASET_UPSERT_KEY_INVALID", field=binding["key"])
            used = binding.get("operations", [operation]) if "filter_ops" in binding else [operation]
            operations = contract["operations"]
            for name in used:
                if name not in operations:
                    operations.append(name)
    return out
