from sqlalchemy import JSON, BigInteger, CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.dataset_formula import Formula, compile_formulas
from ..core.dataset_types import READ_ONLY_KINDS
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
    team_owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL", name="fk_datasets_team_owner"))  # manages a team dataset
    name: Mapped[str]
    name_key: Mapped[str]
    description: Mapped[str | None]
    revision: Mapped[int]
    data_revision: Mapped[int] = mapped_column(BigInteger, default=1, server_default="1")
    auto_number_counter: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    created: Mapped[float]
    updated: Mapped[float]
    columns: Mapped[list["DatasetColumn"]] = relationship(
        cascade="all, delete-orphan", order_by="DatasetColumn.position",
    )

    def compile_formulas(self) -> dict[str, Formula]:
        expressions = {column.key: column.formula["expression"] for column in self.columns
                       if not column.archived and column.formula is not None}
        if not expressions:
            return {}
        fields = {column.key: column.kind for column in self.columns if not column.archived}
        return compile_formulas(fields, expressions)


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True)
    key: Mapped[str] = mapped_column(primary_key=True)
    label: Mapped[str]
    kind: Mapped[str]
    required: Mapped[bool]
    unique: Mapped[bool]
    default_value: Mapped[str | int | float | bool | list[str] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    validation_rules: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    display_format: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    formula: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    options: Mapped[list[str]] = mapped_column(JSON)
    position: Mapped[int]
    archived: Mapped[bool]

    @property
    def read_only(self) -> bool:
        return self.formula is not None or self.kind in READ_ONLY_KINDS


class DatasetRow(Base):
    __tablename__ = "dataset_rows"
    __table_args__ = (Index("ix_dataset_rows_created", "dataset_id", "created", "id"),)

    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    values: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    formula_errors: Mapped[dict[str, str] | None] = mapped_column(JSON(none_as_null=True), nullable=True)
    revision: Mapped[int]
    created: Mapped[float]
    updated: Mapped[float]


class DatasetRowKey(Base):
    __tablename__ = "dataset_row_keys"
    __table_args__ = (
        ForeignKeyConstraint(("dataset_id", "row_id"), ("dataset_rows.dataset_id", "dataset_rows.id"), ondelete="CASCADE"),
        ForeignKeyConstraint(("dataset_id", "field"), ("dataset_columns.dataset_id", "dataset_columns.key"), ondelete="CASCADE"),
        Index("ix_dataset_row_keys_row", "dataset_id", "row_id"),
    )

    dataset_id: Mapped[str] = mapped_column(primary_key=True)
    field: Mapped[str] = mapped_column(primary_key=True)
    value_hash: Mapped[str] = mapped_column(primary_key=True)
    row_id: Mapped[str]
