from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
import json
from time import time
from uuid import uuid4

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.dataset_types import CellValue
from ..core.errors import AppError
from ..models.dataset import Dataset, DatasetColumn, DatasetRow, DatasetRowKey
from .datasets import DatasetRepository

MAX_DATASET_ROWS = 25_000


def key_digest(value: CellValue) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return sha256(json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()


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


def _contains(expression, value: str, postgres: bool):
    return (func.strpos if postgres else func.instr)(expression, value) > 0


def _predicate(spec: RowFilter, dataset_id: str, postgres: bool):
    column, op, value = spec.column, spec.op, spec.value
    expression = _column_value(column)
    if op == "eq" and column.unique:
        ids = select(DatasetRowKey.row_id).where(
            DatasetRowKey.dataset_id == dataset_id, DatasetRowKey.field == column.key,
            DatasetRowKey.value_hash == key_digest(value),
        )
        return DatasetRow.id.in_(ids)
    if op == "contains":
        return _contains(expression, value, postgres)
    if op in {"is_null", "not_null"}:
        return expression.is_(None) if op == "is_null" else expression.is_not(None)
    if column.kind not in {"number", "boolean"}:
        expression = expression.collate("C" if postgres else "BINARY")
    return {
        "eq": expression.__eq__, "ne": expression.__ne__, "lt": expression.__lt__,
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
        postgres = self.datasets.db.engine.dialect.name == "postgresql"
        query = select(DatasetRow).where(DatasetRow.dataset_id == dataset_id)
        if filters:
            combine = or_ if filter_mode == "or" else and_
            query = query.where(combine(*(_predicate(spec, dataset_id, postgres) for spec in filters)))
        if search:
            if not search_columns:
                return []
            query = query.where(or_(*(_contains(_column_value(column), search, postgres) for column in search_columns)))
        order = []
        for sort, descending in sorts:
            expression = _column_value(sort)
            if sort.kind not in {"number", "boolean"}:
                expression = expression.collate("C" if postgres else "BINARY")
            order.append((expression.desc() if descending else expression.asc()).nulls_last())
        query = query.order_by(*(order or [DatasetRow.created]), DatasetRow.id)
        with self.datasets.db.session() as session:
            return list(session.scalars(query.limit(limit).offset(offset)))

    @staticmethod
    def _check_revision(row: DatasetRow, revision: int | None) -> None:
        if revision is not None and row.revision != revision:
            raise AppError("DATASET_ROW_CONFLICT")

    @staticmethod
    def _commit(session: Session) -> None:
        try:
            session.commit()
        except IntegrityError as exc:
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if constraint == "dataset_row_keys_pkey" or "UNIQUE constraint failed: dataset_row_keys." in str(exc.orig):
                raise AppError("DATASET_UNIQUE_CONFLICT") from exc
            raise

    def save(self, uid: str, dataset: Dataset, build_values: Callable[[dict | None], dict], *,
             row_id: str | None = None, revision: int | None = None,
             match: tuple[str, CellValue] | None = None) -> tuple[DatasetRow, bool]:
        with self.datasets.db.session() as session:
            self.datasets.lock(session, uid, dataset.id, dataset.revision)
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
            if row is None:
                count = session.scalar(select(func.count()).select_from(DatasetRow).where(DatasetRow.dataset_id == dataset.id))
                if count >= MAX_DATASET_ROWS:
                    raise AppError("DATASET_ROW_LIMIT", max=MAX_DATASET_ROWS)
                row = DatasetRow(dataset_id=dataset.id, id=uuid4().hex, values=values, revision=1, created=now, updated=now)
                session.add(row)
                session.flush()
            else:
                self._check_revision(row, revision)
                row.values, row.updated, row.revision = values, now, row.revision + 1
                self._clear_keys(session, dataset.id, row.id)
            session.add_all(
                DatasetRowKey(dataset_id=dataset.id, field=column.key, row_id=row.id,
                              value_hash=key_digest(values[column.key]))
                for column in dataset.columns
                if column.unique and not column.archived and values.get(column.key) is not None
            )
            self._commit(session)
            return row, inserted

    @staticmethod
    def _clear_keys(session: Session, dataset_id: str, row_id: str) -> None:
        session.execute(delete(DatasetRowKey).where(DatasetRowKey.dataset_id == dataset_id, DatasetRowKey.row_id == row_id))

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
