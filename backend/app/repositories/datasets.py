from __future__ import annotations

from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..core.dataset_types import key_digest
from ..core.errors import AppError
from ..models.database import Database
from ..models.dataset import Dataset, DatasetColumn, DatasetRow, DatasetRowKey
from ..models.dataset_access import DatasetApiToken, DatasetWorkflowGrant
from ..models.dataset_receipt import DatasetWriteReceipt
from ..models.team import TeamMember
from ..models.workflow import Workflow

UNIQUE_SAMPLE_ROWS = 5
KEY_BATCH = 500


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
             unique: tuple[str, bool] | None = None) -> Dataset:
        """Save a definition under the writer lock. `unique` adds or drops one column's row keys in the same transaction."""
        with self.db.session() as session:
            self.lock(session, uid, dataset.id, revision, advance=True)
            if require_empty and session.scalar(select(DatasetRow.id).where(DatasetRow.dataset_id == dataset.id).limit(1)):
                raise AppError("DATASET_SCHEMA_HAS_ROWS")
            dataset.revision = revision + 1
            result = session.merge(dataset)
            if unique is not None:
                field, enabled = unique
                if enabled:
                    session.flush()
                    self._backfill_keys(session, dataset.id, field)
                else:
                    session.execute(delete(DatasetRowKey).where(
                        DatasetRowKey.dataset_id == dataset.id, DatasetRowKey.field == field,
                    ))
            self._commit(session)
            return result

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
