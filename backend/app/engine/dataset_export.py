"""Build a deployment contract without publishing Studio resource identifiers."""
from dataclasses import asdict, dataclass
from typing import Callable, Iterable

from ..core.dataset_filters import LIST_FILTERS, filter_rules
from ..core.dataset_formula import FormulaDefinitionError, compile_formulas
from ..core.errors import AppError
from . import dataset_nodes


@dataclass
class DatasetExport:
    aliases: dict[str, str]
    bindings: dict[str, dict]

    def formula_programs(self) -> dict:
        """Compile TypeScript's formula programs with the same parser used by Dataset writes."""
        programs = {}
        for name, binding in self.bindings.items():
            columns = binding["columns"]
            definitions = {column["key"]: column["formula"] for column in columns if column.get("formula") is not None}
            if not definitions:
                continue
            try:
                compiled = compile_formulas(
                    {column["key"]: column["kind"] for column in columns},
                    {key: definition["expression"] for key, definition in definitions.items()},
                )
            except FormulaDefinitionError as exc:
                raise AppError("DATASET_FORMULA_INVALID", field=exc.column or "",
                               details={"reason": exc.reason}) from exc
            programs[name] = [
                {"key": key, "definition": definitions[key], "expression": asdict(formula.expression)}
                for key, formula in compiled.items()
            ]
        return programs

    def manifest(self) -> dict:
        return {"format": "superstep/dataset-bindings", "version": 1, "bindings": list(self.bindings.values())}


def prepare(graphs: Iterable[dict], schema: Callable[[str], list[dict]], *, phase3: bool = False) -> DatasetExport:
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
                if not phase3 and any(column.get("formula") for column in columns):
                    raise AppError("DATASET_EXPORT_COLUMN_KIND_UNSUPPORTED")
                out.bindings[alias] = {"name": alias, "columns": columns, "operations": []}
            contract = out.bindings[alias]
            columns = {column["key"]: column for column in contract["columns"]}
            args = binding.get("arguments") or {}
            if not phase3 and (operation == "aggregate_rows" or "aggregate_rows" in binding.get("operations", [])):
                raise AppError("DATASET_EXPORT_AGGREGATE_UNSUPPORTED")
            new_operators = LIST_FILTERS | {"not_contains"}
            if not phase3 and (args.get("filter_tree") is not None
                    or any(rule.get("op") in new_operators for rule in args.get("filters", []))
                    or any(new_operators.intersection(ops) for ops in binding.get("filter_ops", {}).values())):
                raise AppError("DATASET_EXPORT_FILTER_UNSUPPORTED")
            writes = set(args.get("values") or {})
            referenced = {*binding["fields"], *binding.get("filter_ops", {})}
            referenced.update(rule["field"] for _, rule in filter_rules(args))
            referenced.update(rule["field"] for rule in args.get("sorts", []))
            if operation == "delete_row" and "key" in args:
                referenced.add(args["key"])
            agent_writes = dataset_nodes.agent_writes(binding) if "filter_ops" in binding else []
            if agent_writes:
                writes.update(binding["write_fields"])
            if absent := sorted((referenced | writes) - columns.keys()):
                raise AppError("DATASET_BINDING_SCHEMA_MISMATCH", field=absent[0])
            if readonly := sorted(field for field in writes if columns[field].get("formula") is not None):
                raise AppError("DATASET_COLUMN_READ_ONLY", field=readonly[0])
            if not phase3 and any(column.get("validation_rules") for column in columns.values()):
                raise AppError("DATASET_EXPORT_COLUMN_KIND_UNSUPPORTED")
            unsupported = {"long_text", "url", "created_time", "updated_time", "multi_select", "auto_number"}
            if not phase3 and unsupported.intersection(column["kind"] for column in columns.values()):
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
