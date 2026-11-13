import json

from ..core.dataset_types import INVALID_TEXT, TEXT_KINDS, filter_operators, normalize_cell
from ..core.errors import AppError
from ..models.dataset import Dataset, DatasetColumn, DatasetRow
from ..repositories.dataset_rows import ConnectedWrite, DatasetRowRepository, RowFilter, WorkflowWrite
from .dataset_service import DatasetService

MAX_ROW_BYTES = 65_536
MAX_PAGE_BYTES = 1_048_576


def _active_columns(dataset: Dataset) -> dict[str, DatasetColumn]:
    return {column.key: column for column in dataset.columns if not column.archived}


def _column(columns: dict[str, DatasetColumn], field: str) -> DatasetColumn:
    if field not in columns:
        raise AppError("DATASET_COLUMN_NOT_FOUND", details={"field": field})
    return columns[field]


def _normalize(column: DatasetColumn, value, *, required: bool | None = None):
    return normalize_cell(column.key, column.kind, value, column.options,
                          required=column.required if required is None else required)


def _size(payload: dict) -> int:
    return len(json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode())


def _response(row: DatasetRow, columns) -> dict:
    return {
        "id": row.id, "revision": row.revision, "created": row.created, "updated": row.updated,
        "values": {key: row.values.get(key) for key in columns},
    }


def _projection(columns: dict[str, DatasetColumn], fields: list[str] | None):
    return columns if fields is None else {field: _column(columns, field) for field in fields}


def _filter(columns: dict[str, DatasetColumn], field: str, op: str, value) -> RowFilter:
    column = _column(columns, field)
    if op not in filter_operators(column.kind):
        raise AppError("DATASET_FILTER_INVALID", field=field)
    if op in {"is_null", "not_null"}:
        if value is not None:
            raise AppError("DATASET_FILTER_INVALID", field=field)
    elif op == "contains":
        if not isinstance(value, str) or not 0 < len(value) <= 120 or INVALID_TEXT.search(value):
            raise AppError("DATASET_FILTER_INVALID", field=field)
    else:
        value = _normalize(column, value, required=True)
    return RowFilter(column, op, value)


class DatasetRowService:
    def __init__(self, datasets: DatasetService, rows: DatasetRowRepository):
        self.datasets, self.rows = datasets, rows

    def _read_definition(self, uid: str, dataset_id: str, schema_revision: int | None):
        dataset = self.datasets.definition(uid, dataset_id)
        if schema_revision is not None and dataset.revision != schema_revision:
            raise AppError("DATASET_SCHEMA_CONFLICT")
        return dataset

    def get(self, uid: str, dataset_id: str, row_id: str, *, fields: list[str] | None = None, schema_revision: int | None = None) -> dict:
        dataset = self._read_definition(uid, dataset_id, schema_revision)
        row = self.rows.get(dataset.id, row_id)
        if row is None:
            raise AppError("DATASET_ROW_NOT_FOUND")
        columns = _active_columns(dataset)
        return _response(row, _projection(columns, fields))

    def query(self, uid: str, dataset_id: str, *, filters: list[dict], fields: list[str] | None,
              search: str | None, sort: str | None, descending: bool, limit: int, offset: int,
              filter_mode: str = "and", sorts: list[dict] | None = None, schema_revision: int | None = None) -> dict:
        dataset = self._read_definition(uid, dataset_id, schema_revision)
        columns = _active_columns(dataset)
        projection = _projection(columns, fields)
        if search and INVALID_TEXT.search(search):
            raise AppError("DATASET_FILTER_INVALID", field="search")
        if sorts is None:
            sorts = [{"field": sort, "descending": descending}] if sort else []
        rows = self.rows.query(
            dataset.id, filters=[_filter(columns, **spec) for spec in filters], filter_mode=filter_mode, search=search,
            search_columns=[column for column in columns.values() if column.kind in TEXT_KINDS],
            sorts=[(_column(columns, spec["field"]), spec["descending"]) for spec in sorts], limit=limit + 1, offset=offset,
        )
        items = []
        remaining = MAX_PAGE_BYTES
        for row in rows[:limit]:
            item = _response(row, projection)
            remaining -= _size(item)
            if remaining < 0:
                break
            items.append(item)
        return {"items": items, "next_offset": offset + len(items) if len(items) < len(rows) else None,
                "schema_revision": dataset.revision}

    def save(self, uid: str, dataset_id: str, *, values: dict, schema_revision: int | None,
             row_id: str | None = None, revision: int | None = None, key: str | None = None,
             fields: list[str] | None = None, workflow: WorkflowWrite | None = None, dry_run: bool = False,
             connected: ConnectedWrite | None = None) -> dict:
        dataset = self.datasets.editable_definition(uid, dataset_id, schema_revision)
        columns = _active_columns(dataset)
        projection = _projection(columns, fields)
        incoming = {field: _normalize(_column(columns, field), value) for field, value in values.items()}
        match = None
        if key is not None:
            column = _column(columns, key)
            if not column.unique or incoming.get(key) is None:
                raise AppError("DATASET_UPSERT_KEY_INVALID", field=key)
            match = (key, incoming[key])

        def build(previous: dict | None) -> dict:
            result = dict(previous or {})
            for field, column in columns.items():
                if field in incoming:
                    result[field] = incoming[field]
                elif field not in result:
                    result[field] = _normalize(column, column.default_value) if previous is None else None
            if _size(result) > MAX_ROW_BYTES:
                raise AppError("DATASET_ROW_TOO_LARGE", max=MAX_ROW_BYTES)
            return result

        if dry_run:
            found = self.rows.query(dataset.id, filters=[RowFilter(columns[key], "eq", match[1])], filter_mode="and",
                                    search=None, search_columns=[], sorts=[], limit=1, offset=0) if match else []
            current = found[0] if found else None
            values = build(current.values if current is not None else None)
            return {"row": {"id": current.id if current is not None else None,
                            "values": {field: values.get(field) for field in projection}},
                    "inserted": current is None, "dry_run": True}

        row, inserted, replayed = self.rows.save(uid, dataset, build, row_id=row_id, revision=revision, match=match, workflow=workflow, connected=connected)
        if not replayed:
            action = "dataset.row_insert" if inserted else "dataset.row_update"
            context = {"workflow_id": workflow.workflow_id, "run_id": workflow.run_id} if workflow else {}
            if connected:
                context.update(credential_id=connected.token_id, operation=connected.arguments["operation"])
            actor = (workflow.actor_id or uid) if workflow else uid
            self.datasets.audit.record(actor, action, "dataset", dataset.id, row_id=row.id, **context)
        return {"row": _response(row, projection), "inserted": inserted}

    def delete(self, uid: str, dataset_id: str, row_id: str, revision: int | None) -> dict:
        dataset = self.datasets.editable_definition(uid, dataset_id, None)
        self.rows.delete(uid, dataset, row_id, revision)
        self.datasets.audit.record(uid, "dataset.row_delete", "dataset", dataset.id, row_id=row_id)
        return {"ok": True}
