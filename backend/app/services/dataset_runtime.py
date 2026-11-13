"""Bind Dataset execution to the authenticated actor and effective saved workflow."""
from pydantic import ValidationError

from ..core.dataset_types import filter_operators
from ..core.errors import AppError
from ..engine import dataset_nodes
from ..repositories.dataset_rows import WorkflowWrite
from ..schemas.dataset import DatasetRowIn, DatasetRowQuery, DatasetRowUpsert
from .dataset_access import DatasetAccessService
from .dataset_rows import DatasetRowService, _active_columns, _column


class DatasetRuntimeService:
    def __init__(self, access: DatasetAccessService, rows: DatasetRowService):
        self.access, self.rows = access, rows

    def authorize_changes(self, actor: str, before: dict | None, workflow: dict) -> None:
        previous = dataset_nodes.bindings(before)
        for node_id, binding in dataset_nodes.bindings(workflow).items():
            if binding.get("dataset_id") not in (None, "") and binding != previous.get(node_id):
                self._authoring_access(actor, binding)

    def _authoring_access(self, actor: str, binding: dict):
        did, operation = binding.get("dataset_id"), binding.get("operation")
        if not isinstance(did, str) or not 0 < len(did) <= 100:
            raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
        is_agent = "filter_ops" in binding
        agent_writes = dataset_nodes.agent_writes(binding) if is_agent else []
        write = operation in ("insert_row", "upsert_row", "delete_row") or bool(agent_writes)
        definition = self.access.datasets.editable_definition(actor, did, None) if write else self.access.datasets.definition(actor, did)
        # A per-call Agent write binding carries its values; the saved tool binding carries its limits.
        valid = dataset_nodes.valid_agent(binding) if is_agent and operation == "find_rows" else dataset_nodes.valid(binding)
        if not valid:
            return  # the normal graph validator reports incomplete draft configuration
        columns = _active_columns(definition)
        args = binding.get("arguments") or {}
        references = [
            *binding["fields"], *(args.get("values") or {}),
            *(rule["field"] for rule in args.get("filters", [])), *(rule["field"] for rule in args.get("sorts", [])),
        ]
        if operation == "delete_row" and args.get("key"):
            references.append(args["key"])
        if agent_writes:
            references.extend(binding.get("write_fields") or [])
        for field in references:
            _column(columns, field)
        if is_agent:
            for field, operators in binding["filter_ops"].items():
                if set(operators) - set(filter_operators(_column(columns, field).kind)):
                    raise AppError("DATASET_FILTER_INVALID", field=field)
        if operation == "upsert_row" and not _column(columns, args["key"]).unique:
            raise AppError("DATASET_UPSERT_KEY_INVALID", field=args["key"])
        if "upsert_row" in agent_writes and not _column(columns, binding["key"]).unique:
            raise AppError("DATASET_UPSERT_KEY_INVALID", field=binding["key"])
        if operation == "delete_row" and "key" in args and not _column(columns, args["key"]).unique:
            raise AppError("DATASET_UPSERT_KEY_INVALID", field=args["key"])

    def execute(self, *, actor: str, workflow_id: str | None, root_workflow_id: str | None, run_id: str,
                fence: int | None, public: bool, unsaved: bool, dry_run: bool, operation_id: str | None,
                binding: dict, arguments: dict) -> dict:
        if not dataset_nodes.valid(binding):
            raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
        did, operation, fields = binding["dataset_id"], binding["operation"], binding["fields"]
        deleting = operation == "delete_row"
        dataset, workflow, _ = self.access.workflow_dataset(
            actor, workflow_id, did, "read" if deleting else dataset_nodes.ACCESS[operation],
            public=public, deleting=deleting,
        )
        if unsaved:
            self._authoring_access(actor, binding)
        owner = workflow.owner
        if owner is None:
            raise AppError("DATASET_GRANT_DENIED")

        try:
            if operation == "find_rows":
                query = DatasetRowQuery.model_validate({**arguments, "fields": fields})
            elif operation in {"insert_row", "upsert_row"}:
                schema = DatasetRowUpsert if operation == "upsert_row" else DatasetRowIn
                request = schema.model_validate(arguments)
            elif deleting:
                target = dataset_nodes.delete_target(arguments)
        except ValidationError as exc:
            raise AppError("DATASET_NODE_ARGUMENTS_INVALID") from exc

        if operation == "find_rows":
            return self.rows.query(owner, dataset.id, **query.model_dump())
        if operation == "get_row":
            row_id = arguments.get("row_id")
            if not isinstance(row_id, str) or not 0 < len(row_id) <= 100:
                raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
            return self.rows.get(owner, dataset.id, row_id, fields=fields)
        if deleting:
            row_id, key, value = target
            simulate = dry_run or unsaved
            if not simulate and not operation_id:
                raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
            receipt = None if simulate else WorkflowWrite(
                run_id=run_id, workflow_id=workflow.id, operation_id=operation_id,
                arguments={"operation": operation, "fields": fields, "row_id": row_id, "key": key, "value": value},
                fence=fence, run_workflow_id=root_workflow_id, actor_id=actor,
            )
            return self.rows.delete_granted(
                owner, dataset.id, row_id=row_id, key=key, value=value, fields=fields,
                workflow=receipt, dry_run=simulate,
            )
        simulate = dry_run or unsaved
        if not simulate and not operation_id:
            raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
        args = request.model_dump()
        receipt = None if simulate else WorkflowWrite(
            run_id=run_id, workflow_id=workflow.id, operation_id=operation_id,
            arguments={"operation": operation, "fields": fields, **args}, fence=fence,
            run_workflow_id=root_workflow_id, actor_id=actor,
        )
        return self.rows.save(owner, dataset.id, **args, fields=fields, workflow=receipt, dry_run=simulate)
