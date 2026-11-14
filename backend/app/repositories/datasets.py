from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..core.dataset_types import MAX_ROW_BYTES, dataset_size, key_digest
from ..core.errors import AppError
from ..models.database import Database
from ..models.dataset import Dataset, DatasetColumn, DatasetRow, DatasetRowKey
from ..models.dataset_access import DatasetApiToken, DatasetWorkflowGrant
from ..models.dataset_receipt import DatasetWriteReceipt
from ..models.team import TeamMember
from ..models.workflow import Workflow

UNIQUE_SAMPLE_ROWS = 5
KEY_BATCH = 500
CLEAR_BATCH = 500


@dataclass(frozen=True)
class RowChange:
    """One field changed on every row with the definition: cleared, or filled with a default."""
    field: str
    clear: bool = False
    value: object = None
    auto_number: bool = False


def delete_dataset_definitions(session: Session, condition) -> None:
    """Clean up definitions explicitly on SQLite as well as on PostgreSQL."""
    ids = select(Dataset.id).where(condition)
    session.execute(delete(DatasetWriteReceipt).where(DatasetWriteReceipt.dataset_id.in_(ids)))
    session.execute(delete(DatasetApiToken).where(DatasetApiToken.dataset_id.in_(ids)))
    session.execute(delete(DatasetWorkflowGrant).where(DatasetWorkflowGrant.dataset_id.in_(ids)))
    session.execute(delete(DatasetRowKey).where(DatasetRowKey.dataset_id.in_(ids)))
    session.execute(delete(DatasetRow).where(DatasetRow.dataset_id.in_(ids)))
    session.execute(delete(DatasetColumn).where(DatasetColumn.dataset_id.in_(ids)))
    session.execute(delete(Dataset).where(condition))


class DatasetRepository:
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def _visible(uid: str):
        teams = select(TeamMember.team_id).where(TeamMember.user_id == uid)
        return (Dataset.owner_id == uid) | Dataset.team_id.in_(teams)

    def list(self, uid: str, limit: int, offset: int) -> list[Dataset]:
        query = (
            select(Dataset).where(self._visible(uid))
            .order_by(Dataset.name_key, Dataset.id).limit(limit).offset(offset)
        )
        with self.db.session() as session:
            return list(session.scalars(query))

    def get(self, uid: str, dataset_id: str) -> Dataset | None:
        query = (
            select(Dataset).options(joinedload(Dataset.columns))
            .where(Dataset.id == dataset_id, self._visible(uid))
        )
        with self.db.session() as session:
            return session.scalars(query).unique().one_or_none()

    @staticmethod
    def raise_integrity_error(exc: IntegrityError) -> None:
        detail = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if detail in {"uq_datasets_owner_name", "uq_datasets_team_name"} or any(
            f"UNIQUE constraint failed: datasets.{scope}, datasets.name_key" in str(exc.orig)
            for scope in ("owner_id", "team_id")
        ):
            raise AppError("DATASET_NAME_TAKEN") from exc
        raise exc

    def _commit(self, session: Session) -> None:
        try:
            session.commit()
        except IntegrityError as exc:
            self.raise_integrity_error(exc)

    def add(self, dataset: Dataset) -> Dataset:
        with self.db.session() as session:
            session.add(dataset)
            self._commit(session)
        return dataset

    def lock(self, session: Session, uid: str, dataset_id: str, revision: int, *, advance: bool = False) -> None:
        """Serialize writers on both engines and check the schema and membership at the write boundary."""
        result = session.execute(
            update(Dataset).where(
                Dataset.id == dataset_id, Dataset.revision == revision, self._visible(uid),
            ).values(revision=revision + int(advance))
        )
        if result.rowcount != 1:
            raise AppError("DATASET_SCHEMA_CONFLICT")

    def save(self, uid: str, dataset: Dataset, revision: int, *, require_empty: bool = False,
             unique: tuple[str, bool] | None = None, rows: RowChange | None = None) -> tuple[Dataset, int]:
        """Save a definition under the writer lock and return it with the number of rows changed.

        `rows` clears or fills one field on every row, and `unique` adds or drops one column's row keys,
        both in the same transaction as the definition."""
        with self.db.session() as session:
            self.lock(session, uid, dataset.id, revision, advance=True)
            if require_empty and session.scalar(select(DatasetRow.id).where(DatasetRow.dataset_id == dataset.id).limit(1)):
                raise AppError("DATASET_SCHEMA_HAS_ROWS")
            dataset.revision = revision + 1
            dataset.auto_number_counter = session.get(Dataset, dataset.id).auto_number_counter
            result = session.merge(dataset)
            session.flush()
            changed = 0
            if rows is not None:
                if rows.auto_number:
                    changed = self._backfill_auto_numbers(session, dataset.id, rows.field)
                elif rows.clear:
                    changed = self._clear_field(session, dataset.id, rows.field)
                else:
                    changed = self._fill_field(session, dataset.id, rows)
            if unique is not None:
                field, enabled = unique
                if enabled:
                    self._backfill_keys(session, dataset.id, field)
                else:
                    session.execute(delete(DatasetRowKey).where(
                        DatasetRowKey.dataset_id == dataset.id, DatasetRowKey.field == field,
                    ))
            self._commit(session)
            return result, changed

    @staticmethod
    def reserve_auto_numbers(session: Session, dataset_id: str, count: int) -> int:
        """The caller holds the dataset writer lock for this transaction."""
        counter = session.get(Dataset, dataset_id)
        first = counter.auto_number_counter + 1
        counter.auto_number_counter += count
        return first

    def _backfill_auto_numbers(self, session: Session, dataset_id: str, field: str) -> int:
        rows = list(session.scalars(select(DatasetRow).where(DatasetRow.dataset_id == dataset_id)
                                    .order_by(DatasetRow.created, DatasetRow.id)))
        first = self.reserve_auto_numbers(session, dataset_id, len(rows))
        for index, row in enumerate(rows, first):
            row.values = {**row.values, field: index}
            row.revision += 1
        session.flush()
        return len(rows)

    @staticmethod
    def _clear_field(session: Session, dataset_id: str, field: str) -> int:
        """Remove a field from every row in batches. Returns the number of rows that held it."""
        if session.get_bind().dialect.name == "postgresql":
            statement = text(
                'UPDATE dataset_rows SET "values" = "values" - CAST(:field AS text) WHERE dataset_id = :dataset AND id IN ('
                'SELECT id FROM dataset_rows WHERE dataset_id = :dataset AND jsonb_exists("values", :field) LIMIT :batch)'
            )
        else:
            statement = text(
                'UPDATE dataset_rows SET "values" = json_remove("values", :path) WHERE dataset_id = :dataset AND id IN ('
                'SELECT id FROM dataset_rows WHERE dataset_id = :dataset AND json_type("values", :path) IS NOT NULL LIMIT :batch)'
            )
        params = {"dataset": dataset_id, "field": field, "path": f'$."{field}"', "batch": CLEAR_BATCH}
        total = 0
        while True:
            count = session.execute(statement, params).rowcount
            total += count
            if count < CLEAR_BATCH:
                return total

    @staticmethod
    def _fill_field(session: Session, dataset_id: str, change: RowChange) -> int:
        """Write a default into every row after checking that no row would pass the byte limit."""
        extra = dataset_size({change.field: change.value}) - 1
        sizes = select(DatasetRow.values).where(DatasetRow.dataset_id == dataset_id).execution_options(yield_per=KEY_BATCH)
        for values in session.scalars(sizes):
            if dataset_size(values) + extra > MAX_ROW_BYTES:
                raise AppError("DATASET_ROW_TOO_LARGE", max=MAX_ROW_BYTES)
        if session.get_bind().dialect.name == "postgresql":
            statement = text(
                'UPDATE dataset_rows SET "values" = "values" || jsonb_build_object(CAST(:field AS text), CAST(:value AS jsonb)) '
                'WHERE dataset_id = :dataset'
            )
        else:
            statement = text('UPDATE dataset_rows SET "values" = json_set("values", :path, json(:value)) WHERE dataset_id = :dataset')
        return session.execute(statement, {
            "dataset": dataset_id, "field": change.field, "path": f'$."{change.field}"', "value": json.dumps(change.value),
        }).rowcount

    @staticmethod
    def _backfill_keys(session: Session, dataset_id: str, field: str) -> None:
        """Index every non-empty value of `field`, or fail with the duplicate count and sample rows."""
        statement = (
            select(DatasetRow.id, DatasetRow.values[field]).where(DatasetRow.dataset_id == dataset_id)
            .order_by(DatasetRow.created, DatasetRow.id).execution_options(yield_per=KEY_BATCH)
        )
        groups: dict[str, list[str]] = {}
        values: dict[str, object] = {}
        for row_id, value in session.execute(statement):
            if value is None:
                continue
            digest = key_digest(value)
            groups.setdefault(digest, []).append(row_id)
            values.setdefault(digest, value)
        duplicates = [(digest, ids) for digest, ids in groups.items() if len(ids) > 1]
        if duplicates:
            samples = [row_id for _, ids in duplicates for row_id in ids][:UNIQUE_SAMPLE_ROWS]
            raise AppError(
                "DATASET_UNIQUE_DUPLICATES", field=field, count=sum(len(ids) for _, ids in duplicates),
                values=len(duplicates), rows=samples, value=values[duplicates[0][0]],
            )
        keys = [{"dataset_id": dataset_id, "field": field, "value_hash": digest, "row_id": ids[0]}
                for digest, ids in groups.items()]
        for start in range(0, len(keys), KEY_BATCH):
            session.execute(insert(DatasetRowKey), keys[start:start + KEY_BATCH])

    def workflows_mentioning(self, dataset_id: str) -> list[tuple[str, str | None, str | None]]:
        """Saved workflows whose graph text mentions the dataset id, as (id, name, data)."""
        query = select(Workflow.id, Workflow.name, Workflow.data).where(Workflow.data.contains(f'"{dataset_id}"'))
        with self.db.session() as session:
            return [tuple(row) for row in session.execute(query)]

    def delete(self, uid: str, dataset_id: str, revision: int) -> None:
        with self.db.session() as session:
            self.lock(session, uid, dataset_id, revision, advance=True)
            delete_dataset_definitions(session, Dataset.id == dataset_id)
            session.commit()
