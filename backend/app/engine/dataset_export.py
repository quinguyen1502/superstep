"""Build a deployment contract without publishing Studio resource identifiers."""
from dataclasses import dataclass
from typing import Callable, Iterable

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
                columns = [{key: value for key, value in column.items() if key != "label"} for column in schema(did)]
                out.bindings[alias] = {"name": alias, "columns": columns, "operations": []}
            contract = out.bindings[alias]
            columns = {column["key"]: column for column in contract["columns"]}
            args = binding.get("arguments") or {}
            referenced = {*binding["fields"], *(args.get("values") or {}), *binding.get("filter_ops", {})}
            referenced.update(rule["field"] for name in ("filters", "sorts") for rule in args.get(name, []))
            if operation == "delete_row" and "key" in args:
                referenced.add(args["key"])
            if absent := sorted(referenced - columns.keys()):
                raise AppError("DATASET_BINDING_SCHEMA_MISMATCH", field=absent[0])
            if operation in {"upsert_row", "delete_row"} and "key" in args and not columns[args["key"]]["unique"]:
                raise AppError("DATASET_UPSERT_KEY_INVALID", field=args["key"])
            operations = contract["operations"]
            if operation not in operations:
                operations.append(operation)
    return out
