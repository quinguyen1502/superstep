from sqlalchemy import JSON, CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        CheckConstraint("(owner_id IS NULL) <> (team_id IS NULL)", name="ck_datasets_owner"),
        UniqueConstraint("owner_id", "name_key", name="uq_datasets_owner_name"),
        UniqueConstraint("team_id", "name_key", name="uq_datasets_team_name"),
    )

    id: Mapped[str] = mapped_column(primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"))
    name: Mapped[str]
    name_key: Mapped[str]
    description: Mapped[str | None]
    revision: Mapped[int]
    created: Mapped[float]
    updated: Mapped[float]
    columns: Mapped[list["DatasetColumn"]] = relationship(
        cascade="all, delete-orphan", order_by="DatasetColumn.position",
    )


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True)
    key: Mapped[str] = mapped_column(primary_key=True)
    label: Mapped[str]
    kind: Mapped[str]
    required: Mapped[bool]
    unique: Mapped[bool]
    default_value: Mapped[str | int | float | bool | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    options: Mapped[list[str]] = mapped_column(JSON)
    position: Mapped[int]
    archived: Mapped[bool]
