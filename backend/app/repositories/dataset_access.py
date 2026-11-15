from sqlalchemy import delete, select

from ..core.errors import AppError
from ..models.dataset import Dataset
from ..models.dataset_access import DatasetApiToken, DatasetWorkflowGrant
from ..models.workflow import Workflow
from .datasets import DatasetRepository


class DatasetAccessRepository:
    def __init__(self, datasets: DatasetRepository):
        self.datasets = datasets

    def grants(self, dataset_id: str) -> list[tuple[DatasetWorkflowGrant, str | None]]:
        with self.datasets.db.session() as session:
            return list(session.execute(select(DatasetWorkflowGrant, Workflow.name).join(
                Workflow, Workflow.id == DatasetWorkflowGrant.workflow_id,
            ).where(DatasetWorkflowGrant.dataset_id == dataset_id).order_by(DatasetWorkflowGrant.created)))

    def grant(self, dataset_id: str, workflow_id: str) -> DatasetWorkflowGrant | None:
        with self.datasets.db.session() as session:
            return session.get(DatasetWorkflowGrant, (dataset_id, workflow_id))

    def set_grant(self, uid: str, dataset: Dataset, grant: DatasetWorkflowGrant) -> None:
        with self.datasets.db.session() as session:
            self.datasets.lock(session, uid, dataset.id, dataset.revision)
            session.merge(grant)
            session.commit()

    def revoke_grant(self, uid: str, dataset: Dataset, workflow_id: str) -> None:
        with self.datasets.db.session() as session:
            self.datasets.lock(session, uid, dataset.id, dataset.revision)
            session.execute(delete(DatasetWorkflowGrant).where(
                DatasetWorkflowGrant.dataset_id == dataset.id, DatasetWorkflowGrant.workflow_id == workflow_id,
            ))
            session.commit()

    def tokens(self, dataset_id: str) -> list[DatasetApiToken]:
        with self.datasets.db.session() as session:
            return list(session.scalars(select(DatasetApiToken).where(
                DatasetApiToken.dataset_id == dataset_id, DatasetApiToken.revoked.is_(None),
            ).order_by(DatasetApiToken.created)))

    def token_for_hash(self, token_hash: str) -> DatasetApiToken | None:
        with self.datasets.db.session() as session:
            return session.scalar(select(DatasetApiToken).where(
                DatasetApiToken.token_hash == token_hash, DatasetApiToken.revoked.is_(None),
            ))

    def add_token(self, uid: str, dataset: Dataset, token: DatasetApiToken) -> None:
        with self.datasets.db.session() as session:
            self.datasets.lock(session, uid, dataset.id, dataset.revision)
            session.add(token)
            session.commit()

    def change_token(self, uid: str, dataset: Dataset, token_id: str, **changes) -> DatasetApiToken:
        with self.datasets.db.session() as session:
            self.datasets.lock(session, uid, dataset.id, dataset.revision)
            token = session.get(DatasetApiToken, token_id)
            if token is None or token.dataset_id != dataset.id or token.revoked is not None:
                raise AppError("DATASET_TOKEN_NOT_FOUND")
            for key, value in changes.items():
                setattr(token, key, value)
            session.commit()
            return token
