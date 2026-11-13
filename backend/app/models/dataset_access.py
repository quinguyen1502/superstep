from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DatasetWorkflowGrant(Base):
    __tablename__ = "dataset_workflow_grants"
    __table_args__ = (
        CheckConstraint("permission in ('read', 'write', 'read_write')", name="ck_dataset_grants_permission"),
        Index("ix_dataset_grants_workflow", "workflow_id"),
    )

    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), primary_key=True)
    permission: Mapped[str]
    created: Mapped[float]


class DatasetApiToken(Base):
    __tablename__ = "dataset_api_tokens"
    __table_args__ = (
        CheckConstraint("permission in ('read', 'write', 'read_write')", name="ck_dataset_tokens_permission"),
        Index("ix_dataset_tokens_dataset", "dataset_id"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    issuer_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str]
    permission: Mapped[str]
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    prefix: Mapped[str]
    created: Mapped[float]
    revoked: Mapped[float | None]
