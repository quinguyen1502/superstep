from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DatasetShare(Base):
    __tablename__ = "dataset_shares"
    __table_args__ = (Index("ix_dataset_shares_dataset", "dataset_id", "revoked", "created"),)

    id: Mapped[str] = mapped_column(primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    name: Mapped[str]
    fields: Mapped[list[str]] = mapped_column(JSON)
    filter_tree: Mapped[dict | None] = mapped_column(JSON(none_as_null=True))
    schema_signature: Mapped[dict] = mapped_column(JSON)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created: Mapped[float]
    updated: Mapped[float]
    revoked: Mapped[float | None]
