from time import time

from ..core import config
from ..core.dataset_types import INVALID_TEXT, MAX_DATASET_ROWS, MAX_PAGE_BYTES, MAX_ROW_BYTES, TEXT_KINDS, dataset_size, filter_operators, normalize_cell
from ..core.errors import AppError
from ..models.dataset import Dataset, DatasetColumn, DatasetRow
from ..repositories.dataset_rows import ConnectedWrite, DatasetRowRepository, RowFilter, WorkflowWrite
from .dataset_service import DatasetService

def _active_columns(dataset: Dataset) -> dict[str, DatasetColumn]:
    return {column.key: column for column in dataset.columns if not column.archived}


def _column(columns: dict[str, DatasetColumn], field: str) -> DatasetColumn:
    if field not in columns:
        raise AppError("DATASET_COLUMN_NOT_FOUND", details={"field": field})
    return columns[field]


def _normalize(column: DatasetColumn, value, *, required: bool | None = None):
    return normalize_cell(column.key, column.kind, value, column.options,
                          required=column.required if required is None else required)


def _response(row: DatasetRow, columns) -> dict:
    return {
        "id": row.id, "revision": row.revision, "created": row.created, "updated": row.updated,
        "values": {key: row.values.get(key) for key in columns},
    }


def _write_result(row: DatasetRow, inserted: bool, projection) -> dict:
    """The one insert/upsert outcome shape. `projection` is None for a caller that may not read values."""
    # An identifier-only replay can refer to a row that has since been deleted.
    if projection is None or row.values is None:
        return {"row": {"id": row.id, "revision": row.revision}, "inserted": inserted}
    return {"row": _response(row, projection), "inserted": inserted}


def _write_projection(columns: dict[str, DatasetColumn], fields: list[str] | None, readable: bool):
    """Resolve the output projection of a write before anything is stored.

    A caller without read permission never receives cell values, so a requested projection is refused
    instead of being silently dropped. An empty field list asks for identifiers only.
    """
    if not readable:
        if fields:
            raise AppError("DATASET_GRANT_DENIED")
        return None
    if fields is not None and not fields:
        return None
    return _projection(columns, fields)


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

    def expire_receipts(self) -> int:
        return self.rows.expire_receipts(time() - config.dataset_receipt_days() * 86400)

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

    def export_rows(self, uid: str, dataset_id: str, limit: int) -> list[dict]:
        """Rows the caller can read, for an explicit project snapshot. `limit` includes one extra probe row."""
        dataset = self._read_definition(uid, dataset_id, None)
        rows = self.rows.query(
            dataset.id, filters=[], filter_mode="and", search=None, search_columns=[], sorts=[], limit=limit, offset=0,
        )
        return [_response(row, _active_columns(dataset)) for row in rows]

    def query(self, uid: str, dataset_id: str, *, filters: list[dict], fields: list[str] | None,
              search: str | None, sort: str | None, descending: bool, limit: int, offset: int,
              filter_mode: str = "and", sorts: list[dict] | None = None, schema_revision: int | None = None,
              include_total: bool = False) -> dict:
        dataset = self._read_definition(uid, dataset_id, schema_revision)
        columns = _active_columns(dataset)
        projection = _projection(columns, fields)
        if search and INVALID_TEXT.search(search):
            raise AppError("DATASET_FILTER_INVALID", field="search")
        if sorts is None:
            sorts = [{"field": sort, "descending": descending}] if sort else []
        predicates = []
        for position, spec in enumerate(filters, start=1):
            try:
                predicates.append(_filter(columns, **spec))
            except AppError as exc:
                raise AppError("DATASET_FILTER_INVALID", field=spec["field"],
                               details={"field": spec["field"], "position": position}) from exc
        rows, total = self.rows.query_page(
            dataset.id, filters=predicates, filter_mode=filter_mode, search=search,
            search_columns=[column for column in columns.values() if column.kind in TEXT_KINDS],
            sorts=[(_column(columns, spec["field"]), spec["descending"]) for spec in sorts], limit=limit + 1, offset=offset, include_total=include_total,
        )
        items = []
        remaining = MAX_PAGE_BYTES
        for row in rows[:limit]:
            item = _response(row, projection)
            remaining -= dataset_size(item)
            if remaining < 0:
                break
            items.append(item)
        return {"items": items, "next_offset": offset + len(items) if len(items) < len(rows) else None,
                "schema_revision": dataset.revision,
                **({"total": min(total, MAX_DATASET_ROWS), "total_capped": total > MAX_DATASET_ROWS}
                   if total is not None else {})}

    def save(self, uid: str, dataset_id: str, *, values: dict, schema_revision: int | None,
             row_id: str | None = None, revision: int | None = None, key: str | None = None,
             fields: list[str] | None = None, workflow: WorkflowWrite | None = None, dry_run: bool = False,
             connected: ConnectedWrite | None = None, readable: bool = True) -> dict:
        dataset = self.datasets.editable_definition(uid, dataset_id, schema_revision)
        columns = _active_columns(dataset)
        projection = _write_projection(columns, fields, readable)
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
            if dataset_size(result) > MAX_ROW_BYTES:
                raise AppError("DATASET_ROW_TOO_LARGE", max=MAX_ROW_BYTES)
            return result

        if dry_run:
            found = self.rows.query(dataset.id, filters=[RowFilter(columns[key], "eq", match[1])], filter_mode="and",
                                    search=None, search_columns=[], sorts=[], limit=1, offset=0) if match else []
            current = found[0] if found else None
            values = build(current.values if current is not None else None)
            if projection is None:
                row = {"id": current.id if current is not None else None,
                       "revision": current.revision if current is not None else None}
            else:
                row = {"id": current.id if current is not None else None,
                       "values": {field: values.get(field) for field in projection}}
            return {"row": row, "inserted": current is None, "dry_run": True}

        row, inserted, replayed, changed = self.rows.save(
            uid, dataset, build, row_id=row_id, revision=revision, match=match, workflow=workflow, connected=connected,
            reveal=projection is not None and (workflow is not None or connected is not None),
        )
        if not replayed and changed:
            action = "dataset.row_insert" if inserted else "dataset.row_update"
            context = {"workflow_id": workflow.workflow_id, "run_id": workflow.run_id} if workflow else {}
            if connected:
                context.update(credential_id=connected.token_id, operation=connected.arguments["operation"])
            actor = (workflow.actor_id or uid) if workflow else uid
            self.datasets.audit.record(actor, action, "dataset", dataset.id, row_id=row.id, **context)
        return _write_result(row, inserted, projection)

    def delete_granted(self, uid: str, dataset_id: str, *, row_id: str | None = None, key: str | None = None,
                       value=None, schema_revision: int | None = None, fields: list[str] | None = None,
                       workflow: WorkflowWrite | None = None, dry_run: bool = False,
                       connected: ConnectedWrite | None = None) -> dict:
        dataset = self.datasets.editable_definition(uid, dataset_id, schema_revision)
        columns = _active_columns(dataset)
        if fields is not None:
            _projection(columns, fields)
        match = None
        if key is not None:
            column = _column(columns, key)
            if not column.unique or (value := _normalize(column, value)) is None:
                raise AppError("DATASET_UPSERT_KEY_INVALID", field=key)
            match = (key, value)
        if dry_run:
            found = self._granted_row_id(dataset, columns, row_id, match)
            if found is None:
                raise AppError("DATASET_ROW_NOT_FOUND")
            return {"row_id": found, "deleted": True, "dry_run": True}
        deleted_id, replayed = self.rows.remove(uid, dataset, row_id=row_id, match=match, workflow=workflow, connected=connected)
        if not replayed:
            context = {"workflow_id": workflow.workflow_id, "run_id": workflow.run_id} if workflow else {}
            if connected:
                context.update(credential_id=connected.token_id, operation="delete_row")
            actor = (workflow.actor_id or uid) if workflow else uid
            self.datasets.audit.record(actor, "dataset.row_delete", "dataset", dataset.id, row_id=deleted_id, **context)
        return {"row_id": deleted_id, "deleted": True}

    def _granted_row_id(self, dataset: Dataset, columns: dict, row_id: str | None, match: tuple[str, object] | None):
        if match is None:
            row = self.rows.get(dataset.id, row_id or "")
            return None if row is None else row.id
        field, value = match
        found = self.rows.query(dataset.id, filters=[RowFilter(columns[field], "eq", value)], filter_mode="and",
                                search=None, search_columns=[], sorts=[], limit=1, offset=0)
        return found[0].id if found else None

    def delete(self, uid: str, dataset_id: str, row_id: str, revision: int) -> dict:
        dataset = self.datasets.editable_definition(uid, dataset_id, None)
        self.rows.delete(uid, dataset, row_id, revision)
        self.datasets.audit.record(uid, "dataset.row_delete", "dataset", dataset.id, row_id=row_id)
        return {"ok": True}
