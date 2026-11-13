"""Run the portable Dataset contract with a dataset-scoped deployment credential."""
from pydantic import ValidationError

from ..core.dataset_types import TEXT_KINDS
from ..core.errors import AppError
from ..engine.dataset_nodes import ACCESS, delete_target, valid
from ..repositories.dataset_rows import ConnectedWrite
from ..schemas.dataset import DatasetConnectedInput, DatasetRowIn, DatasetRowQuery, DatasetRowUpsert
from .dataset_access import DatasetAccessService, can_read
from .dataset_rows import DatasetRowService, _active_columns


class DatasetConnectedService:
    def __init__(self, access: DatasetAccessService, rows: DatasetRowService):
        self.access, self.rows = access, rows

    def execute(self, dataset_id: str, secret: str, request: DatasetConnectedInput) -> dict:
        operation, arguments, fields = request.operation, request.arguments, request.fields
        deleting = operation == "delete_row"
        dataset, token = self.access.token_dataset(
            secret, dataset_id, "read" if deleting else ACCESS[operation], deleting=deleting,
        )
        if not valid({"dataset_id": dataset_id, "operation": operation, "fields": fields, "arguments": arguments}):
            raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
        write = ACCESS[operation] == "write"
        if (write or deleting) != (request.operation_id is not None):
            raise AppError("DATASET_NODE_ARGUMENTS_INVALID")

        columns = _active_columns(dataset)
        expected = {column.key: column for column in request.columns}
        if len(expected) != len(request.columns):
            raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
        referenced = {*fields}
        if operation == "find_rows":
            referenced.update(rule["field"] for name in ("filters", "sorts") for rule in arguments.get(name, []))
            if arguments.get("search"):
                referenced.update(column.key for column in columns.values() if column.kind in TEXT_KINDS)
        if write:
            referenced.update(arguments["values"])
        if deleting and "key" in arguments:
            referenced.add(arguments["key"])
        if absent := sorted(referenced - expected.keys()):
            raise AppError("DATASET_BINDING_SCHEMA_MISMATCH", field=absent[0])
        for field, contract in expected.items():
            column = columns.get(field)
            if (column is None or column.kind != contract.kind or column.unique != contract.unique
                    or column.required != contract.required or column.default_value != contract.default
                    or set(column.options) != set(contract.options)):
                raise AppError("DATASET_BINDING_SCHEMA_MISMATCH", field=field)
        if write:
            for field in columns.keys() - expected.keys():
                column = columns[field]
                if column.required and column.default_value is None:
                    raise AppError("DATASET_BINDING_SCHEMA_MISMATCH", field=field)

        try:
            if operation == "find_rows":
                query = DatasetRowQuery.model_validate({**arguments, "fields": fields})
            elif write:
                schema = DatasetRowUpsert if operation == "upsert_row" else DatasetRowIn
                payload = schema.model_validate(arguments).model_dump(exclude={"schema_revision"})
            elif deleting:
                target = delete_target(arguments)
        except ValidationError as exc:
            raise AppError("DATASET_NODE_ARGUMENTS_INVALID") from exc

        uid = token.issuer_id
        if deleting:
            row_id, key, value = target
            receipt = ConnectedWrite(token.id, token.token_hash, request.operation_id,
                                     {"operation": operation, "fields": fields, "row_id": row_id, "key": key, "value": value})
            return self.rows.delete_granted(
                uid, dataset_id, row_id=row_id, key=key, value=value, schema_revision=dataset.revision,
                fields=fields, connected=receipt,
            )
        if write:
            receipt = ConnectedWrite(token.id, token.token_hash, request.operation_id,
                                     {"operation": operation, "fields": fields, "arguments": payload})
            return self.rows.save(uid, dataset_id, schema_revision=dataset.revision, fields=fields,
                                  connected=receipt, readable=can_read(token.permission), **payload)
        if operation == "find_rows":
            result = self.rows.query(uid, dataset_id, schema_revision=dataset.revision, **query.model_dump())
        else:
            row_id = arguments["row_id"]
            if len(row_id) > 100:
                raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
            result = self.rows.get(uid, dataset_id, row_id, fields=fields, schema_revision=dataset.revision)
        self.access.datasets.audit.record(uid, "dataset.connected_read", "dataset", dataset_id,
                                          credential_id=token.id, operation=operation)
        return result
