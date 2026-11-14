"""Standalone Python Dataset runtime embedded in the exported graph."""
from inspect import getsource

from ..core import dataset_types
from ..schemas import dataset
from .dataset_nodes import INPUTS


def python_standalone() -> str:
    # Keep the generated value and request contract identical to the connected API.
    operation_inputs = {operation: sorted(args) for operation, args in INPUTS.items()}
    shared = [
        getsource(dataset_types).split("from .errors import AppError\n", 1)[1],
        "ColumnKey = Annotated[str, Field(pattern=COLUMN_KEY_PATTERN)]",
        f"DATASET_OPERATION_INPUTS = {operation_inputs!r}",
        "RowValues = Annotated[dict[ColumnKey, CellValue], Field(max_length=100)]",
        *(getsource(cls) for cls in (dataset.DatasetFilter, dataset.DatasetSort, dataset.DatasetRowQuery,
                                     dataset.DatasetRowIn, dataset.DatasetRowUpsert)),
    ]
    return "\n".join((IMPORTS, *shared, STANDALONE))


IMPORTS = r'''
# --- Standalone Dataset storage --------------------------------------------------------------------------------
import json
import math
import re
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
from time import time as dataset_now
from typing import Annotated, Literal, TypeAlias, get_args

import sqlalchemy as sa
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


class AppError(RuntimeError):
    def __init__(self, code: str, **details):
        self.code = code
        super().__init__(f"{code}: " + ", ".join(f"{key}={value}" for key, value in details.items()) if details else code)
'''

STANDALONE = r'''
DATASET_METADATA = sa.MetaData()
DATASET_DEFINITIONS = sa.Table("superstep_dataset_definitions", DATASET_METADATA,
    sa.Column("dataset_id", sa.String(100), primary_key=True),
    sa.Column("contract", sa.JSON, nullable=False),
)
DATASET_ROWS = sa.Table("superstep_dataset_rows", DATASET_METADATA,
    sa.Column("dataset_id", sa.String(100), sa.ForeignKey(DATASET_DEFINITIONS.c.dataset_id), primary_key=True),
    sa.Column("id", sa.String(32), primary_key=True),
    sa.Column("values", sa.JSON, nullable=False),
    sa.Column("revision", sa.Integer, nullable=False),
    sa.Column("created", sa.Float, nullable=False),
    sa.Column("updated", sa.Float, nullable=False),
)
sa.Index("ix_superstep_dataset_rows_order", DATASET_ROWS.c.dataset_id, DATASET_ROWS.c.created, DATASET_ROWS.c.id)
DATASET_KEYS = sa.Table("superstep_dataset_keys", DATASET_METADATA,
    sa.Column("dataset_id", sa.String(100), primary_key=True),
    sa.Column("field", sa.String(63), primary_key=True),
    sa.Column("digest", sa.String(64), primary_key=True),
    sa.Column("row_id", sa.String(32), nullable=False),
    sa.ForeignKeyConstraint(["dataset_id", "row_id"], [DATASET_ROWS.c.dataset_id, DATASET_ROWS.c.id]),
)
sa.Index("ix_superstep_dataset_keys_row", DATASET_KEYS.c.dataset_id, DATASET_KEYS.c.row_id)
DATASET_RECEIPTS = sa.Table("superstep_dataset_receipts", DATASET_METADATA,
    sa.Column("dataset_id", sa.String(100), sa.ForeignKey(DATASET_DEFINITIONS.c.dataset_id), primary_key=True),
    sa.Column("operation_id", sa.String(128), primary_key=True),
    sa.Column("fingerprint", sa.String(64), nullable=False),
    sa.Column("result", sa.JSON, nullable=False),
    sa.Column("created", sa.Float, nullable=False),
)


def dataset_backend(binding: str) -> str:
    setting = f"{binding}_BACKEND"
    backend = os.getenv(setting)
    if not backend:
        raise AppError("DATASET_BINDING_MISSING", setting=setting, choices="superstep, sqlite, postgresql")
    if backend not in {"superstep", "sqlite", "postgresql"}:
        raise AppError("DATASET_BINDING_INVALID", setting=setting, choices="superstep, sqlite, postgresql")
    return backend


def dataset_database(binding: str, backend: str, *, setup: bool = False):
    dataset_id = os.getenv(f"{binding}_ID", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", dataset_id):
        raise AppError("DATASET_BINDING_INVALID", setting=f"{binding}_ID")
    if backend == "sqlite":
        path = os.getenv(f"{binding}_SQLITE_PATH")
        if not path or path == ":memory:":
            raise AppError("DATASET_BINDING_MISSING", setting=f"{binding}_SQLITE_PATH")
        location = Path(path).expanduser().resolve()
        if not setup and not location.is_file():
            raise AppError("DATASET_SETUP_REQUIRED", binding=binding)
        url = sa.URL.create("sqlite+pysqlite", database=location.as_uri(),
                            query={"uri": "true", "mode": "rwc" if setup else "rw", "timeout": "10"})
    else:
        dsn = os.getenv(f"{binding}_POSTGRES_DSN")
        if not dsn:
            raise AppError("DATASET_BINDING_MISSING", setting=f"{binding}_POSTGRES_DSN")
        try:
            url = sa.make_url(dsn)
        except (ValueError, sa.exc.ArgumentError):
            raise AppError("DATASET_BINDING_INVALID", setting=f"{binding}_POSTGRES_DSN") from None
        if url.drivername not in {"postgresql", "postgresql+psycopg"} or not url.database:
            raise AppError("DATASET_BINDING_INVALID", setting=f"{binding}_POSTGRES_DSN")
        url = url.set(drivername="postgresql+psycopg")
    try:
        options = {"connect_args": {"connect_timeout": 10}} if backend == "postgresql" else {}
        engine = sa.create_engine(url, poolclass=sa.pool.NullPool, hide_parameters=True, **options)
    except (ImportError, ValueError, sa.exc.SQLAlchemyError):
        raise AppError("DATASET_STORAGE_ERROR", binding=binding) from None
    if backend == "sqlite":
        @sa.event.listens_for(engine, "connect")
        def register_fold(dbapi_connection, _record):
            dbapi_connection.create_function(TEXT_FOLD_FUNCTION, 1, fold_text, deterministic=True)
    return engine, dataset_id


def dataset_contract(binding: str) -> dict:
    columns = DATASET_BINDINGS[binding]["columns"]
    return {"version": 1, "columns": {column["key"]: {**column, "options": sorted(column["options"])} for column in columns}}


def dataset_check_schema(connection, dataset_id: str, binding: str) -> None:
    stored = connection.scalar(sa.select(DATASET_DEFINITIONS.c.contract).where(DATASET_DEFINITIONS.c.dataset_id == dataset_id))
    if stored is None:
        raise AppError("DATASET_SETUP_REQUIRED", binding=binding)
    if stored != dataset_contract(binding):
        raise AppError("DATASET_BINDING_SCHEMA_MISMATCH", binding=binding)


def dataset_check_storage(connection, binding: str) -> None:
    inspector = sa.inspect(connection)
    if not all(inspector.has_table(table.name) for table in DATASET_METADATA.sorted_tables) or not any(
        column["name"] == "created" for column in inspector.get_columns(DATASET_RECEIPTS.name)
    ):
        raise AppError("DATASET_SETUP_REQUIRED", binding=binding)


def dataset_restore_snapshot(connection, dataset_id: str, binding: str) -> None:
    path = Path(__file__).with_name("dataset-snapshots.json")
    if not path.is_file():
        return
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise AppError("DATASET_SNAPSHOT_INVALID", binding=binding) from None
    snapshots = document.get("snapshots") if isinstance(document, dict) else None
    if not isinstance(snapshots, list):
        raise AppError("DATASET_SNAPSHOT_INVALID", binding=binding)
    chosen = next((item for item in snapshots if isinstance(item, dict) and item.get("binding") == binding), None)
    if chosen is None:
        return
    contract = dataset_contract(binding)
    rows = chosen.get("rows")
    if chosen.get("contract") != contract:
        raise AppError("DATASET_BINDING_SCHEMA_MISMATCH", binding=binding)
    if not isinstance(rows, list):
        raise AppError("DATASET_SNAPSHOT_INVALID", binding=binding)
    if len(rows) > SNAPSHOT_MAX_ROWS:
        raise AppError("DATASET_SNAPSHOT_TOO_LARGE", max=SNAPSHOT_MAX_ROWS)
    columns = contract["columns"]
    prepared = []
    for item in rows:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not re.fullmatch(r"[a-f0-9]{32}", item["id"]):
            raise AppError("DATASET_SNAPSHOT_INVALID", binding=binding)
        values = item.get("values")
        if not isinstance(values, dict) or set(values) - set(columns):
            raise AppError("DATASET_BINDING_SCHEMA_MISMATCH", binding=binding)
        try:
            stored = {field: dataset_normalize(column, values[field] if field in values else column["default"]) for field, column in columns.items()}
        except AppError:
            raise AppError("DATASET_BINDING_SCHEMA_MISMATCH", binding=binding) from None
        if dataset_size(stored) > MAX_ROW_BYTES:
            raise AppError("DATASET_ROW_TOO_LARGE", max=MAX_ROW_BYTES)
        prepared.append((item["id"], stored))
    for row_id, stored in prepared:
        if connection.scalar(sa.select(DATASET_ROWS.c.id).where(DATASET_ROWS.c.dataset_id == dataset_id, DATASET_ROWS.c.id == row_id)) is not None:
            continue
        count = connection.scalar(sa.select(sa.func.count()).select_from(DATASET_ROWS).where(DATASET_ROWS.c.dataset_id == dataset_id))
        if count >= MAX_DATASET_ROWS:
            raise AppError("DATASET_ROW_LIMIT", max=MAX_DATASET_ROWS)
        now = dataset_now()
        connection.execute(DATASET_ROWS.insert().values(dataset_id=dataset_id, id=row_id, values=stored, revision=1, created=now, updated=now))
        entries = [{"dataset_id": dataset_id, "field": field, "digest": key_digest(stored[field]), "row_id": row_id}
                   for field, column in columns.items() if column["unique"] and stored.get(field) is not None]
        if entries:
            try:
                connection.execute(DATASET_KEYS.insert(), entries)
            except sa.exc.IntegrityError:
                raise AppError("DATASET_UNIQUE_CONFLICT") from None


def setup_datasets(*, create: bool) -> None:
    for binding in DATASET_BINDINGS:
        backend = dataset_backend(binding)
        if backend == "superstep":
            continue
        engine, dataset_id = dataset_database(binding, backend, setup=create)
        try:
            with engine.begin() as connection:
                if create and backend == "sqlite":
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                if create:
                    DATASET_METADATA.create_all(connection)
                    dataset_migrate_receipts(connection, backend == "postgresql")
                    insert = postgres_insert if backend == "postgresql" else sqlite_insert
                    connection.execute(insert(DATASET_DEFINITIONS).values(dataset_id=dataset_id, contract=dataset_contract(binding))
                                       .on_conflict_do_nothing(index_elements=[DATASET_DEFINITIONS.c.dataset_id]))
                else:
                    dataset_check_storage(connection, binding)
                dataset_check_schema(connection, dataset_id, binding)
                if create:
                    dataset_restore_snapshot(connection, dataset_id, binding)
        except sa.exc.SQLAlchemyError:
            raise AppError("DATASET_STORAGE_ERROR", binding=binding) from None
        finally:
            engine.dispose()


def dataset_migrate_receipts(connection, postgres: bool) -> None:
    receipts = DATASET_RECEIPTS
    if postgres:
        connection.exec_driver_sql("LOCK TABLE superstep_dataset_receipts IN ACCESS EXCLUSIVE MODE")
    if any(column["name"] == "created" for column in sa.inspect(connection).get_columns(receipts.name)):
        return
    connection.exec_driver_sql(
        "ALTER TABLE superstep_dataset_receipts ADD COLUMN created DOUBLE PRECISION NOT NULL DEFAULT 0"
    )
    key = (receipts.c.dataset_id, receipts.c.operation_id)
    base = sa.select(*key, receipts.c.result).order_by(*key).limit(200)
    batch = base
    now = dataset_now()
    while rows := connection.execute(batch).all():
        for dataset_id, operation_id, result in rows:
            legacy = result.get("row")
            if legacy is not None:
                result = {"row_id": legacy["id"], "revision": legacy["revision"], "inserted": result["inserted"]}
            connection.execute(receipts.update().where(
                key[0] == dataset_id, key[1] == operation_id,
            ).values(result=result, created=now))
        batch = base.where(sa.tuple_(*key) > sa.tuple_(*rows[-1][:2]))


def dataset_expire_receipts(connection, dataset_id: str) -> None:
    try:
        days = max(1, int(os.getenv("STUDIO_DATASET_RECEIPT_DAYS", "30")))
    except ValueError:
        days = 30
    connection.execute(DATASET_RECEIPTS.delete().where(
        DATASET_RECEIPTS.c.dataset_id == dataset_id, DATASET_RECEIPTS.c.created < dataset_now() - days * 86400,
    ))


def dataset_column(columns: dict, field: str) -> dict:
    if field not in columns:
        raise AppError("DATASET_COLUMN_NOT_FOUND", field=field)
    return columns[field]


def dataset_normalize(column: dict, value, *, required: bool | None = None):
    return normalize_cell(column["key"], column["kind"], value, column["options"],
                          required=column["required"] if required is None else required)


def dataset_row_payload(row, fields: list[str]) -> dict:
    return {"id": row.id, "revision": row.revision, "created": row.created, "updated": row.updated,
            "values": {field: row["values"].get(field) for field in fields}}


def dataset_expression(column: dict, postgres: bool):
    value = DATASET_ROWS.c["values"][column["key"]]
    if column["kind"] == "number":
        return value.as_float()
    if column["kind"] == "boolean":
        return value.as_boolean()
    return value.as_string().collate("C" if postgres else "BINARY")


def dataset_fold(expression, connection):
    if connection.dialect.name != "postgresql":
        return getattr(sa.func, TEXT_FOLD_FUNCTION)(expression)
    marker = "dataset_fold_collation"
    if marker not in connection.info:
        names = set(connection.execute(sa.text(
            "SELECT collname FROM pg_collation WHERE collname IN ('und-x-icu', 'pg_c_utf8')"
        )).scalars())
        connection.info[marker] = next((name for name in ("und-x-icu", "pg_c_utf8") if name in names), None)
    collation = connection.info[marker]
    return sa.func.lower(expression.collate(collation) if collation else expression.collate("default")).collate("C")


def dataset_contains(expression, value: str, connection):
    position = sa.func.strpos if connection.dialect.name == "postgresql" else sa.func.instr
    return position(dataset_fold(expression, connection), dataset_fold(sa.literal(value), connection)) > 0


def dataset_filter(columns: dict, rule: DatasetFilter, dataset_id: str, connection):
    postgres = connection.dialect.name == "postgresql"
    column = dataset_column(columns, rule.field)
    expression = dataset_expression(column, postgres)
    op, value = rule.op, rule.value
    if op not in filter_operators(column["kind"]):
        raise AppError("DATASET_FILTER_INVALID", field=rule.field)
    if op in {"is_null", "not_null"}:
        if value is not None:
            raise AppError("DATASET_FILTER_INVALID", field=rule.field)
        return expression.is_(None) if op == "is_null" else expression.is_not(None)
    if op == "contains":
        if not isinstance(value, str) or not 0 < len(value) <= 120 or INVALID_TEXT.search(value):
            raise AppError("DATASET_FILTER_INVALID", field=rule.field)
        return dataset_contains(expression, value, connection)
    value = dataset_normalize(column, value, required=True)
    if op == "eq" and column["unique"]:
        ids = sa.select(DATASET_KEYS.c.row_id).where(DATASET_KEYS.c.dataset_id == dataset_id,
                                                     DATASET_KEYS.c.field == rule.field,
                                                     DATASET_KEYS.c.digest == key_digest(value))
        return DATASET_ROWS.c.id.in_(ids)
    if op == "ne":
        return expression.is_distinct_from(value)
    compare = {"eq": expression.__eq__, "lt": expression.__lt__,
               "lte": expression.__le__, "gt": expression.__gt__, "gte": expression.__ge__}
    return compare[op](value)


def dataset_find(connection, query, dataset_id: str, columns: dict, fields: list[str], arguments: dict) -> dict:
    params = DatasetRowQuery.model_validate(arguments)
    postgres = connection.dialect.name == "postgresql"
    if params.filters:
        combine = sa.or_ if params.filter_mode == "or" else sa.and_
        query = query.where(combine(*(dataset_filter(columns, rule, dataset_id, connection) for rule in params.filters)))
    if params.search:
        if INVALID_TEXT.search(params.search):
            raise AppError("DATASET_FILTER_INVALID", field="search")
        terms = [dataset_contains(dataset_expression(column, postgres), params.search, connection)
                 for column in columns.values() if column["kind"] in TEXT_KINDS]
        query = query.where(sa.or_(*terms) if terms else sa.false())
    order = []
    for sort in params.sorts or []:
        column = dataset_column(columns, sort.field)
        expr = dataset_expression(column, postgres)
        keys = [expr] if column["kind"] in {"number", "boolean"} else [dataset_fold(expr, connection), expr]
        order.extend((key.desc() if sort.descending else key.asc()).nulls_last() for key in keys)
    query = query.order_by(*(order or [DATASET_ROWS.c.created]), DATASET_ROWS.c.id)
    rows = connection.execute(query.offset(params.offset).limit(params.limit + 1)).mappings()
    items, remaining = [], MAX_PAGE_BYTES
    for row in rows:
        if len(items) == params.limit:
            return {"items": items, "next_offset": params.offset + len(items), "schema_revision": 1}
        item = dataset_row_payload(row, fields)
        remaining -= dataset_size(item)
        if remaining < 0:
            return {"items": items, "next_offset": params.offset + len(items), "schema_revision": 1}
        items.append(item)
    return {"items": items, "next_offset": None, "schema_revision": 1}


def dataset_write(connection, query, dataset_id: str, columns: dict, operation: str, fields: list[str],
                  arguments: dict, operation_id: str) -> dict:
    if not isinstance(operation_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", operation_id):
        raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
    schema = DatasetRowUpsert if operation == "upsert_row" else DatasetRowIn
    request = schema.model_validate(arguments)
    incoming = {key: dataset_normalize(dataset_column(columns, key), value) for key, value in request.values.items()}
    key = request.key if operation == "upsert_row" else None
    if key and (not dataset_column(columns, key)["unique"] or incoming.get(key) is None):
        raise AppError("DATASET_UPSERT_KEY_INVALID", field=key)
    fingerprint = write_fingerprint({"operation": operation, "fields": fields, "arguments": request.model_dump()})
    receipts = DATASET_RECEIPTS
    previous = connection.execute(sa.select(receipts).where(receipts.c.dataset_id == dataset_id,
                                                             receipts.c.operation_id == operation_id)).mappings().one_or_none()
    if previous is not None:
        if previous.fingerprint != fingerprint:
            raise AppError("DATASET_RECEIPT_CONFLICT")
        result = previous.result
        row = connection.execute(query.where(DATASET_ROWS.c.id == result["row_id"])).mappings().one_or_none()
        outcome = dataset_row_payload(row, fields) if row is not None and fields else {
            "id": result["row_id"], "revision": row.revision if row is not None else result["revision"],
        }
        return {"row": outcome, "inserted": result["inserted"]}
    row = None
    keys = DATASET_KEYS
    if key:
        row_id = connection.scalar(sa.select(keys.c.row_id).where(keys.c.dataset_id == dataset_id,
                                   keys.c.field == key, keys.c.digest == key_digest(incoming[key])))
        if row_id:
            row = connection.execute(query.where(DATASET_ROWS.c.id == row_id)).mappings().one()
    if row is None:
        count = connection.scalar(sa.select(sa.func.count()).select_from(DATASET_ROWS).where(DATASET_ROWS.c.dataset_id == dataset_id))
        if count >= MAX_DATASET_ROWS:
            raise AppError("DATASET_ROW_LIMIT", max=MAX_DATASET_ROWS)
        values = {field: incoming[field] if field in incoming else dataset_normalize(column, column["default"])
                  for field, column in columns.items()}
    else:
        values = {**row["values"], **incoming}
    if dataset_size(values) > MAX_ROW_BYTES:
        raise AppError("DATASET_ROW_TOO_LARGE", max=MAX_ROW_BYTES)
    now = dataset_now()
    row_id = row.id if row is not None else uuid.uuid4().hex
    if row is None:
        connection.execute(DATASET_ROWS.insert().values(dataset_id=dataset_id, id=row_id, values=values, revision=1, created=now, updated=now))
    elif values != row["values"]:
        connection.execute(DATASET_ROWS.update().where(DATASET_ROWS.c.dataset_id == dataset_id, DATASET_ROWS.c.id == row_id)
                           .values(values=values, revision=row.revision + 1, updated=now))
        connection.execute(keys.delete().where(keys.c.dataset_id == dataset_id, keys.c.row_id == row_id))
    entries = [{"dataset_id": dataset_id, "field": field, "digest": key_digest(values[field]), "row_id": row_id}
               for field, column in columns.items() if column["unique"] and values.get(field) is not None]
    if entries and (row is None or values != row["values"]):
        try:
            connection.execute(keys.insert(), entries)
        except sa.exc.IntegrityError:
            raise AppError("DATASET_UNIQUE_CONFLICT") from None
    stored = connection.execute(query.where(DATASET_ROWS.c.id == row_id)).mappings().one()
    # An empty field list asks for identifiers only, the shape a write-only connected token receives.
    outcome = dataset_row_payload(stored, fields) if fields else {"id": stored["id"], "revision": stored["revision"]}
    result = {"row": outcome, "inserted": row is None}
    connection.execute(receipts.insert().values(dataset_id=dataset_id, operation_id=operation_id,
                                                fingerprint=fingerprint, created=now,
                                                result={"row_id": row_id, "revision": stored.revision, "inserted": row is None}))
    return result


def dataset_delete(connection, query, dataset_id: str, columns: dict, fields: list[str], arguments: dict,
                   operation_id: str) -> dict:
    if not isinstance(operation_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", operation_id):
        raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
    by_id = set(arguments) == {"row_id"}
    if not by_id and set(arguments) != {"key", "value"}:
        raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
    keys = DATASET_KEYS
    if by_id:
        row_id = arguments["row_id"]
        if not isinstance(row_id, str) or not 0 < len(row_id) <= 100:
            raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
        target = {"row_id": row_id, "key": None, "value": None}
    else:
        key, value = arguments["key"], arguments["value"]
        if not isinstance(key, str):
            raise AppError("DATASET_UPSERT_KEY_INVALID", field=key)
        column = dataset_column(columns, key)
        if not column["unique"] or isinstance(value, (dict, list)):
            raise AppError("DATASET_UPSERT_KEY_INVALID", field=key)
        value = dataset_normalize(column, value, required=False)
        if value is None:
            raise AppError("DATASET_UPSERT_KEY_INVALID", field=key)
        target = {"row_id": None, "key": key, "value": value}
    fingerprint = write_fingerprint({"operation": "delete_row", "fields": fields, "arguments": target})
    receipts = DATASET_RECEIPTS
    previous = connection.execute(sa.select(receipts).where(receipts.c.dataset_id == dataset_id,
                                                             receipts.c.operation_id == operation_id)).mappings().one_or_none()
    if previous is not None:
        if previous.fingerprint != fingerprint:
            raise AppError("DATASET_RECEIPT_CONFLICT")
        return previous.result
    if not by_id:
        row_id = connection.scalar(sa.select(keys.c.row_id).where(keys.c.dataset_id == dataset_id,
                                   keys.c.field == target["key"], keys.c.digest == key_digest(target["value"])))
    row = connection.execute(query.where(DATASET_ROWS.c.id == row_id)).mappings().one_or_none() if row_id else None
    if row is None:
        raise AppError("DATASET_ROW_NOT_FOUND")  # a missed delete stores no receipt
    connection.execute(keys.delete().where(keys.c.dataset_id == dataset_id, keys.c.row_id == row.id))
    connection.execute(DATASET_ROWS.delete().where(DATASET_ROWS.c.dataset_id == dataset_id, DATASET_ROWS.c.id == row.id))
    result = {"row_id": row.id, "deleted": True}
    connection.execute(receipts.insert().values(dataset_id=dataset_id, operation_id=operation_id,
                                                fingerprint=fingerprint, result=result, created=dataset_now()))
    return result


def dataset_standalone(binding: str, backend: str, operation: str, fields: list[str], arguments: dict,
                       operation_id: str | None) -> dict:
    columns = dataset_contract(binding)["columns"]
    allowed = DATASET_OPERATION_INPUTS.get(operation)
    if (allowed is None or not isinstance(arguments, dict) or set(arguments) - set(allowed)
            or (not fields and operation not in {"insert_row", "upsert_row"}) or len(fields) != len(set(fields))):
        raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
    for field in fields:
        dataset_column(columns, field)
    engine, dataset_id = dataset_database(binding, backend)
    try:
        with engine.begin() as connection:
            write = operation in {"insert_row", "upsert_row", "delete_row"}
            dataset_check_storage(connection, binding)
            if write:
                # Insert, upsert and delete take the writer lock before reading the receipt or the key.
                connection.execute(DATASET_DEFINITIONS.update().where(DATASET_DEFINITIONS.c.dataset_id == dataset_id)
                                   .values(dataset_id=DATASET_DEFINITIONS.c.dataset_id))
                dataset_expire_receipts(connection, dataset_id)
            dataset_check_schema(connection, dataset_id, binding)
            query = sa.select(DATASET_ROWS).where(DATASET_ROWS.c.dataset_id == dataset_id)
            if operation == "delete_row":
                return dataset_delete(connection, query, dataset_id, columns, fields, arguments, operation_id)
            if write:
                return dataset_write(connection, query, dataset_id, columns, operation, fields, arguments, operation_id)
            if operation == "find_rows":
                return dataset_find(connection, query, dataset_id, columns, fields, arguments)
            if operation == "get_row":
                row_id = arguments.get("row_id")
                if set(arguments) != {"row_id"} or not isinstance(row_id, str) or not 0 < len(row_id) <= 100:
                    raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
                row = connection.execute(query.where(DATASET_ROWS.c.id == row_id)).mappings().one_or_none()
                if row is None:
                    raise AppError("DATASET_ROW_NOT_FOUND")
                return dataset_row_payload(row, fields)
            raise AppError("DATASET_NODE_ARGUMENTS_INVALID")
    except ValidationError:
        raise AppError("DATASET_NODE_ARGUMENTS_INVALID") from None
    except sa.exc.SQLAlchemyError:
        raise AppError("DATASET_STORAGE_ERROR", binding=binding) from None
    finally:
        engine.dispose()
'''
