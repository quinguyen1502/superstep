from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..core.dataset_types import CellValue, ColumnKind

ColumnKey = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,62}$")]
Label = Annotated[str, Field(min_length=1, max_length=120)]
Option = Annotated[str, Field(min_length=1, max_length=120)]


class DatasetColumnIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    key: ColumnKey
    label: Label
    kind: ColumnKind
    required: bool = False
    unique: bool = False
    default: CellValue = None
    options: list[Option] = Field(default_factory=list, max_length=100)


class DatasetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: Label
    description: str | None = Field(default=None, max_length=2_000)
    team_id: str | None = Field(default=None, min_length=1, max_length=100)
    columns: list[DatasetColumnIn] = Field(default_factory=list, max_length=100)


class DatasetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: Label
    description: str | None = Field(default=None, max_length=2_000)
    revision: int = Field(ge=1)


class DatasetColumnUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    column: DatasetColumnIn
    revision: int = Field(ge=1)


RowValues = Annotated[dict[ColumnKey, CellValue], Field(max_length=100)]


class DatasetRowIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    values: RowValues
    schema_revision: int | None = Field(default=None, ge=1)


class DatasetRowUpdate(DatasetRowIn):
    revision: int = Field(ge=1)


class DatasetRowUpsert(DatasetRowIn):
    key: ColumnKey


class DatasetFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    field: ColumnKey
    op: Literal["eq", "ne", "lt", "lte", "gt", "gte", "contains", "is_null", "not_null"]
    value: CellValue = None


class DatasetSort(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    field: ColumnKey
    descending: bool = False


class DatasetRowQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    filters: list[DatasetFilter] = Field(default_factory=list, max_length=12)
    filter_mode: Literal["and", "or"] = "and"
    fields: list[ColumnKey] | None = Field(default=None, max_length=100)
    search: str | None = Field(default=None, max_length=120)
    sort: ColumnKey | None = None
    descending: bool = False
    sorts: list[DatasetSort] | None = Field(default=None, max_length=12)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=25_000)


DatasetPermission = Literal["read", "write", "read_write"]


class DatasetGrantInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    permission: DatasetPermission


class DatasetTokenInput(DatasetGrantInput):
    name: Annotated[str, Field(min_length=1, max_length=80)]
