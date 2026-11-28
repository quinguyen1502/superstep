from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ..core.errors import AppError
from ..models.dataset import Dataset
from ..models.dataset_share import DatasetShare
from .datasets import DatasetRepository


class DatasetShareRepository:
    def __init__(self, datasets: DatasetRepository):
        self.datasets = datasets

    @staticmethod
    def _active(dataset_id: str):
        return DatasetShare.dataset_id == dataset_id, DatasetShare.revoked.is_(None)

    def list(self, dataset_id: str, limit: int, offset: int) -> list[DatasetShare]:
        statement = (
            select(DatasetShare).where(*self._active(dataset_id))
            .order_by(DatasetShare.created, DatasetShare.id).limit(limit).offset(offset)
        )
        with self.datasets.db.session() as session:
            return list(session.scalars(statement))

    @staticmethod
    def _get(session, dataset_id, share_id) -> DatasetShare:
        share = session.get(DatasetShare, share_id)
        if share is None or share.dataset_id != dataset_id or share.revoked is not None:
            raise AppError("DATASET_SHARE_NOT_FOUND")
        return share

    def get(self, dataset_id: str, share_id: str) -> DatasetShare:
        with self.datasets.db.session() as session:
            return self._get(session, dataset_id, share_id)

    def add(self, uid: str, dataset: Dataset, share: DatasetShare) -> None:
        with self.datasets.db.session() as session:
            self.datasets.lock(session, uid, dataset.id, dataset.revision)
            session.add(share)
            session.commit()

    def change(self, uid: str, dataset: Dataset, share_id: str, **changes) -> DatasetShare:
        with self.datasets.db.session() as session:
            self.datasets.lock(session, uid, dataset.id, dataset.revision)
            share = self._get(session, dataset.id, share_id)
            for key, value in changes.items():
                setattr(share, key, value)
            session.commit()
            return share

    def resolve(self, token_hash: str) -> tuple[DatasetShare, Dataset] | None:
        statement = (
            select(DatasetShare, Dataset).join(Dataset, Dataset.id == DatasetShare.dataset_id)
            .options(joinedload(Dataset.columns))
            .where(DatasetShare.token_hash == token_hash, DatasetShare.revoked.is_(None))
        )
        with self.datasets.db.session() as session:
            result = session.execute(statement).unique().one_or_none()
            return None if result is None else (result[0], result[1])

    def is_current(self, dataset_id: str, revision: int, token_hash: str) -> bool:
        statement = (
            select(DatasetShare.id).join(Dataset, Dataset.id == DatasetShare.dataset_id)
            .where(*self._active(dataset_id), DatasetShare.token_hash == token_hash, Dataset.revision == revision)
        )
        with self.datasets.db.session() as session:
            return session.scalar(statement) is not None
