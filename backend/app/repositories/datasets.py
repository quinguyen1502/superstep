from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..core.errors import AppError
from ..models.database import Database
from ..models.dataset import Dataset, DatasetColumn, DatasetRow, DatasetRowKey
from ..models.dataset_access import DatasetApiToken, DatasetWorkflowGrant
from ..models.team import TeamMember


def delete_dataset_definitions(session: Session, condition) -> None:
    """Clean up definitions explicitly on SQLite as well as on PostgreSQL."""
    ids = select(Dataset.id).where(condition)
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
    def _commit(session: Session) -> None:
        try:
            session.commit()
        except IntegrityError as exc:
            detail = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if detail in {"uq_datasets_owner_name", "uq_datasets_team_name"} or any(
                f"UNIQUE constraint failed: datasets.{scope}, datasets.name_key" in str(exc.orig)
                for scope in ("owner_id", "team_id")
            ):
                raise AppError("DATASET_NAME_TAKEN") from exc
            raise

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

    def save(self, uid: str, dataset: Dataset, revision: int, *, require_empty: bool = False) -> Dataset:
        with self.db.session() as session:
            self.lock(session, uid, dataset.id, revision, advance=True)
            if require_empty and session.scalar(select(DatasetRow.id).where(DatasetRow.dataset_id == dataset.id).limit(1)):
                raise AppError("DATASET_SCHEMA_HAS_ROWS")
            dataset.revision = revision + 1
            result = session.merge(dataset)
            self._commit(session)
            return result

    def delete(self, uid: str, dataset_id: str, revision: int) -> None:
        with self.db.session() as session:
            self.lock(session, uid, dataset_id, revision, advance=True)
            delete_dataset_definitions(session, Dataset.id == dataset_id)
            session.commit()
