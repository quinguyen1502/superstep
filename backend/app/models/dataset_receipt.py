from sqlalchemy import ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class DatasetWriteReceipt(Base):
    __tablename__ = "dataset_write_receipts"
    __table_args__ = (
        UniqueConstraint("scope", "operation_id", name="uq_dataset_write_identity"),
        Index("ix_dataset_write_receipts_created", "created"),
    )

    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True)
    scope: Mapped[str] = mapped_column(String(128), primary_key=True)
    operation_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    created: Mapped[float]
