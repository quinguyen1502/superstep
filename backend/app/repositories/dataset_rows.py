from collections.abc import Callable, Iterator
from dataclasses import dataclass
from time import time
from uuid import uuid4

from sqlalchemy import and_, delete, func, literal, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.dataset_types import MAX_DATASET_ROWS, TEXT_FOLD_FUNCTION, CellValue, key_digest, write_fingerprint
from ..core.errors import AppError
from ..models.dataset import Dataset, DatasetColumn, DatasetRow, DatasetRowKey
from ..models.dataset_access import DatasetApiToken, DatasetWorkflowGrant
from ..models.dataset_receipt import DatasetWriteReceipt
from ..models.run import Run
from .datasets import DatasetRepository
from .runs import StaleLease

@dataclass(frozen=True)
class WorkflowWrite:
    run_id: str
    workflow_id: str
    operation_id: str
    arguments: dict
    fence: int | None = None
    run_workflow_id: str | None = None
    actor_id: str | None = None

    @property
    def fingerprint(self) -> str:
        return write_fingerprint([self.workflow_id, self.arguments])

    @property
    def scope(self) -> str:
        return f"run:{self.run_id}"


@dataclass(frozen=True)
class ConnectedWrite:
    token_id: str
    token_hash: str
    operation_id: str
    arguments: dict

    @property
    def fingerprint(self) -> str:
        return write_fingerprint(self.arguments)

    @property
    def scope(self) -> str:
        return f"token:{self.token_id}"


@dataclass(frozen=True)
class RowFilter:
    column: DatasetColumn
    op: str
    value: CellValue


def _column_value(column: DatasetColumn):
    value = DatasetRow.values[column.key]
    if column.kind == "number":
        return value.as_float()
    if column.kind == "boolean":
        return value.as_boolean()
    return value.as_string()


FOLD_COLLATIONS = ("und-x-icu", "pg_c_utf8")  # Unicode case mapping that does not depend on the server locale


def _fold_collation(engine) -> str | None:
    """The PostgreSQL collation `lower` folds with: ICU or the builtin UTF-8 provider when present, else the database default."""
    if not hasattr(engine, "_dataset_fold_collation"):
        with engine.connect() as connection:
            names = set(connection.execute(
                text("SELECT collname FROM pg_collation WHERE collname = ANY(:names)"), {"names": list(FOLD_COLLATIONS)},
            ).scalars())
        engine._dataset_fold_collation = next((name for name in FOLD_COLLATIONS if name in names), None)
    return engine._dataset_fold_collation


@dataclass(frozen=True)
class _Text:
    """Dialect-specific text expressions: exact comparison and one Unicode case fold for both databases."""
    postgres: bool
    collation: str | None = None

    def exact(self, expression):
        return expression.collate("C" if self.postgres else "BINARY")

    def fold(self, expression):
        if not self.postgres:
            return getattr(func, TEXT_FOLD_FUNCTION)(expression)
        folded = func.lower(expression.collate(self.collation) if self.collation else expression)
        return folded.collate("C")

    def contains(self, expression, value: str):
        position = func.strpos if self.postgres else func.instr
        return position(self.fold(expression), self.fold(literal(value))) > 0


def _predicate(spec: RowFilter, dataset_id: str, texts: _Text):
    column, op, value = spec.column, spec.op, spec.value
    expression = _column_value(column)
    if op == "eq" and column.unique:
        ids = select(DatasetRowKey.row_id).where(
            DatasetRowKey.dataset_id == dataset_id, DatasetRowKey.field == column.key,
            DatasetRowKey.value_hash == key_digest(value),
        )
        return DatasetRow.id.in_(ids)
    if op == "contains":
        return texts.contains(expression, value)
    if op in {"is_null", "not_null"}:
        return expression.is_(None) if op == "is_null" else expression.is_not(None)
    if column.kind not in {"number", "boolean"}:
        expression = texts.exact(expression)
    if op == "ne":
        return expression.is_distinct_from(value)
    return {
        "eq": expression.__eq__, "lt": expression.__lt__,
        "lte": expression.__le__, "gt": expression.__gt__, "gte": expression.__ge__,
    }[op](value)


class DatasetRowRepository:
    def __init__(self, datasets: DatasetRepository):
        self.datasets = datasets

    def get(self, dataset_id: str, row_id: str) -> DatasetRow | None:
        with self.datasets.db.session() as session:
            return session.get(DatasetRow, (dataset_id, row_id))

    def query(self, dataset_id: str, *, filters: list[RowFilter], filter_mode: str, search: str | None,
              search_columns: list[DatasetColumn], sorts: list[tuple[DatasetColumn, bool]],
              limit: int, offset: int) -> list[DatasetRow]:
        engine = self.datasets.db.engine
        postgres = engine.dialect.name == "postgresql"
        texts = _Text(postgres, _fold_collation(engine) if postgres else None)
        query = select(DatasetRow).where(DatasetRow.dataset_id == dataset_id)
        if filters:
            combine = or_ if filter_mode == "or" else and_
            query = query.where(combine(*(_predicate(spec, dataset_id, texts) for spec in filters)))
        if search:
            if not search_columns:
                return []
            query = query.where(or_(*(texts.contains(_column_value(column), search) for column in search_columns)))
        order = []
        for sort, descending in sorts:
            expression = _column_value(sort)
            keys = [expression]
            if sort.kind not in {"number", "boolean"}:
                keys = [texts.fold(expression), texts.exact(expression)]  # case-insensitive, then exact as the tiebreak
            order.extend((key.desc() if descending else key.asc()).nulls_last() for key in keys)
        query = query.order_by(*(order or [DatasetRow.created]), DatasetRow.id)
        with self.datasets.db.session() as session:
            return list(session.scalars(query.limit(limit).offset(offset)))

    @staticmethod
    def _check_revision(row: DatasetRow, revision: int | None) -> None:
        if revision is not None and row.revision != revision:
            raise AppError("DATASET_ROW_CONFLICT")

    def _commit(self, session: Session) -> None:
        try:
            self.datasets._commit(session)
        except IntegrityError as exc:
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if constraint == "uq_dataset_write_identity" or "UNIQUE constraint failed: dataset_write_receipts.scope" in str(exc.orig):
                raise AppError("DATASET_RECEIPT_CONFLICT") from exc
            if constraint == "dataset_row_keys_pkey" or "UNIQUE constraint failed: dataset_row_keys." in str(exc.orig):
                raise AppError("DATASET_UNIQUE_CONFLICT") from exc
            raise

    def save(self, uid: str, dataset: Dataset, build_values: Callable[[dict | None], dict], *,
             row_id: str | None = None, revision: int | None = None,
             match: tuple[str, CellValue] | None = None, workflow: WorkflowWrite | None = None,
             connected: ConnectedWrite | None = None, reveal: bool = False) -> tuple[DatasetRow, bool, bool, bool]:
        """Insert or update one row under the writer lock.

        Returns the row, whether it was inserted, whether a receipt was replayed, and whether stored values
        changed. `reveal` means the caller will see cell values; it is re-checked against the locked grant or
        token so a concurrent downgrade to write-only fails closed.
        """
        receipt = workflow or connected
        with self.datasets.db.session() as session:
            if workflow and workflow.fence is not None:
                checked = session.execute(update(Run).where(
                    Run.id == workflow.run_id, Run.workflow_id == (workflow.run_workflow_id or workflow.workflow_id),
                    Run.lease_gen == workflow.fence,
                ).values(lease_gen=Run.lease_gen))
                if checked.rowcount != 1:
                    raise StaleLease(workflow.run_id)
            self.datasets.lock(session, uid, dataset.id, dataset.revision)
            if workflow:
                grant = session.get(DatasetWorkflowGrant, (dataset.id, workflow.workflow_id))
                if grant is None or grant.permission not in {"write", "read_write"}:
                    raise AppError("DATASET_GRANT_DENIED")
                if reveal and grant.permission != "read_write":
                    raise AppError("DATASET_GRANT_DENIED")
            if connected:
                token = session.get(DatasetApiToken, connected.token_id)
                if (token is None or token.dataset_id != dataset.id or token.issuer_id != uid
                        or token.token_hash != connected.token_hash or token.revoked is not None
                        or token.permission not in {"write", "read_write"}):
                    raise AppError("AUTH_TOKEN_INVALID")
                if reveal and token.permission != "read_write":
                    raise AppError("DATASET_GRANT_DENIED")
            if receipt:
                fingerprint = receipt.fingerprint
                scope = receipt.scope
                previous = session.scalar(select(DatasetWriteReceipt).where(
                    DatasetWriteReceipt.scope == scope, DatasetWriteReceipt.operation_id == receipt.operation_id,
                ))
                if previous is not None:
                    if previous.dataset_id != dataset.id or previous.fingerprint != fingerprint:
                        raise AppError("DATASET_RECEIPT_CONFLICT")
                    snapshot = previous.result
                    return DatasetRow(dataset_id=dataset.id, **snapshot["row"]), snapshot["inserted"], True, False
            if match is not None:
                field, value = match
                key = session.get(DatasetRowKey, (dataset.id, field, key_digest(value)))
                row_id = key.row_id if key is not None else None
            row = session.get(DatasetRow, (dataset.id, row_id)) if row_id is not None else None
            if row is None and row_id is not None:
                raise AppError("DATASET_ROW_NOT_FOUND")
            values = build_values(row.values if row is not None else None)
            now = time()
            inserted = row is None
            changed = inserted or values != row.values
            if row is None:
                count = session.scalar(select(func.count()).select_from(DatasetRow).where(DatasetRow.dataset_id == dataset.id))
                if count >= MAX_DATASET_ROWS:
                    raise AppError("DATASET_ROW_LIMIT", max=MAX_DATASET_ROWS)
                row = DatasetRow(dataset_id=dataset.id, id=uuid4().hex, values=values, revision=1, created=now, updated=now)
                session.add(row)
                session.flush()
            else:
                self._check_revision(row, revision)
            if changed and not inserted:
                row.values, row.updated, row.revision = values, now, row.revision + 1
                self._clear_keys(session, dataset.id, row.id)
            if changed:
                session.add_all(self._keys(dataset, row))
            if receipt:
                result = {"row": {"id": row.id, "values": row.values, "revision": row.revision,
                                  "created": row.created, "updated": row.updated}, "inserted": inserted}
                session.add(DatasetWriteReceipt(dataset_id=dataset.id, scope=scope, operation_id=receipt.operation_id,
                                                fingerprint=fingerprint, result=result, created=now))
            self._commit(session)
            return row, inserted, False, changed

    @staticmethod
    def _keys(dataset: Dataset, row: DatasetRow) -> Iterator[DatasetRowKey]:
        for column in dataset.columns:
            value = row.values.get(column.key)
            if column.unique and not column.archived and value is not None:
                yield DatasetRowKey(dataset_id=dataset.id, field=column.key, row_id=row.id, value_hash=key_digest(value))

    def matching_keys(self, dataset_id: str, field: str, hashes: set[str]) -> set[str]:
        candidates = sorted(hashes)
        found: set[str] = set()
        with self.datasets.db.session() as session:
            for start in range(0, len(candidates), 200):
                found.update(session.scalars(select(DatasetRowKey.value_hash).where(
                    DatasetRowKey.dataset_id == dataset_id, DatasetRowKey.field == field,
                    DatasetRowKey.value_hash.in_(candidates[start:start + 200]),
                )))
        return found

    def import_rows(self, uid: str, dataset: Dataset, values: list[dict], *, create: bool) -> None:
        with self.datasets.db.session() as session:
            if create:
                session.add(dataset)
                try:
                    session.flush()
                except IntegrityError as exc:
                    self.datasets.raise_integrity_error(exc)
            self.datasets.lock(session, uid, dataset.id, dataset.revision)
            count = session.scalar(select(func.count()).select_from(DatasetRow).where(DatasetRow.dataset_id == dataset.id))
            if count + len(values) > MAX_DATASET_ROWS:
                raise AppError("DATASET_ROW_LIMIT", max=MAX_DATASET_ROWS)
            now = time()
            rows = [DatasetRow(dataset_id=dataset.id, id=uuid4().hex, values=record, revision=1,
                               created=now + index / 1_000_000, updated=now + index / 1_000_000)
                    for index, record in enumerate(values)]
            session.add_all(rows)
            session.flush()
            session.add_all(key for row in rows for key in self._keys(dataset, row))
            self._commit(session)

    def export_values(self, uid: str, dataset_id: str) -> Iterator[dict]:
        statement = select(DatasetRow.values).join(Dataset, DatasetRow.dataset_id == Dataset.id).where(
            DatasetRow.dataset_id == dataset_id, self.datasets._visible(uid),
        ).order_by(DatasetRow.created, DatasetRow.id).execution_options(yield_per=128)
        with self.datasets.db.session() as session:
            yield from session.scalars(statement)

    @staticmethod
    def _clear_keys(session: Session, dataset_id: str, row_id: str) -> None:
        session.execute(delete(DatasetRowKey).where(DatasetRowKey.dataset_id == dataset_id, DatasetRowKey.row_id == row_id))

    def remove(self, uid: str, dataset: Dataset, *, row_id: str | None, match: tuple[str, CellValue] | None,
               workflow: WorkflowWrite | None = None, connected: ConnectedWrite | None = None) -> tuple[str, bool]:
        receipt = workflow or connected
        with self.datasets.db.session() as session:
            if workflow and workflow.fence is not None:
                checked = session.execute(update(Run).where(
                    Run.id == workflow.run_id, Run.workflow_id == (workflow.run_workflow_id or workflow.workflow_id),
                    Run.lease_gen == workflow.fence,
                ).values(lease_gen=Run.lease_gen))
                if checked.rowcount != 1:
                    raise StaleLease(workflow.run_id)
            self.datasets.lock(session, uid, dataset.id, dataset.revision)
            if workflow:
                grant = session.get(DatasetWorkflowGrant, (dataset.id, workflow.workflow_id))
                if grant is None or not grant.allow_delete:
                    raise AppError("DATASET_GRANT_DENIED")
            if connected:
                token = session.get(DatasetApiToken, connected.token_id)
                if (token is None or token.dataset_id != dataset.id or token.issuer_id != uid
                        or token.token_hash != connected.token_hash or token.revoked is not None
                        or not token.allow_delete):
                    raise AppError("AUTH_TOKEN_INVALID")
            if receipt:
                fingerprint, scope = receipt.fingerprint, receipt.scope
                previous = session.scalar(select(DatasetWriteReceipt).where(
                    DatasetWriteReceipt.scope == scope, DatasetWriteReceipt.operation_id == receipt.operation_id,
                ))
                if previous is not None:
                    if previous.dataset_id != dataset.id or previous.fingerprint != fingerprint:
                        raise AppError("DATASET_RECEIPT_CONFLICT")
                    return previous.result["row_id"], True
            if match is not None:
                field, value = match
                key = session.get(DatasetRowKey, (dataset.id, field, key_digest(value)))
                row_id = key.row_id if key is not None else None
            row = session.get(DatasetRow, (dataset.id, row_id)) if row_id is not None else None
            if row is None:
                raise AppError("DATASET_ROW_NOT_FOUND")
            deleted_id = row.id
            self._clear_keys(session, dataset.id, deleted_id)
            session.delete(row)
            if receipt:
                session.add(DatasetWriteReceipt(
                    dataset_id=dataset.id, scope=scope, operation_id=receipt.operation_id, fingerprint=fingerprint,
                    result={"row_id": deleted_id, "deleted": True}, created=time(),
                ))
            self._commit(session)
            return deleted_id, False

    def delete(self, uid: str, dataset: Dataset, row_id: str, revision: int | None) -> None:
        with self.datasets.db.session() as session:
            self.datasets.lock(session, uid, dataset.id, dataset.revision)
            row = session.get(DatasetRow, (dataset.id, row_id))
            if row is None:
                raise AppError("DATASET_ROW_NOT_FOUND")
            self._check_revision(row, revision)
            self._clear_keys(session, dataset.id, row_id)
            session.delete(row)
            session.commit()
