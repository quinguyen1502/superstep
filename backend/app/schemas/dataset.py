from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..core.dataset_filters import MAX_FILTER_VALUES, tree_rules
from ..core.dataset_types import COLUMN_KEY_PATTERN, CellValue, ColumnKind, DatasetValue, FilterOperator, SummaryFunction

ColumnKey = Annotated[str, Field(pattern=COLUMN_KEY_PATTERN)]
Label = Annotated[str, Field(min_length=1, max_length=120)]
Option = Annotated[str, Field(min_length=1, max_length=120)]


class DatasetFieldContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    key: ColumnKey
    kind: ColumnKind
    required: bool = False
    unique: bool = False
    default: DatasetValue = None
    options: list[Option] = Field(default_factory=list, max_length=100)


class DatasetColumnIn(DatasetFieldContract):
    label: Label

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


class DatasetOwnerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    user_id: str = Field(min_length=1, max_length=100)
    revision: int = Field(ge=1)


class DatasetColumnUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    column: DatasetColumnIn
    revision: int = Field(ge=1)


RowValues = Annotated[dict[ColumnKey, DatasetValue], Field(max_length=100)]


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
    op: FilterOperator
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



class DatasetQueryFilter(DatasetFilter):
    value: CellValue | Annotated[list[CellValue], Field(max_length=MAX_FILTER_VALUES)] = None


class DatasetFilterRule(DatasetQueryFilter):
    type: Literal["rule"]


class DatasetFilterGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["group"]
    conjunction: Literal["and", "or"]
    children: list[Annotated[DatasetFilterRule | DatasetFilterGroup, Field(discriminator="type")]]


class DatasetFilterQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    filter_mode: Literal["and", "or"] = "and"
    search: str | None = Field(default=None, max_length=120)
    filters: list[DatasetQueryFilter] = Field(default_factory=list, max_length=12)
    filter_tree: DatasetFilterGroup | None = None

    @field_validator("filter_tree", mode="before")
    @classmethod
    def bound_tree(cls, tree):
        if tree is not None:
            for _ in tree_rules(tree):
                pass
        return tree

    @model_validator(mode="after")
    def choose_filter_form(self):
        if self.filter_tree is not None and {"filters", "filter_mode"} & self.model_fields_set:
            raise ValueError("Use either filter_tree or flat filters")
        return self


class DatasetGroupedRowQuery(DatasetFilterQuery, DatasetRowQuery):
    pass


class DatasetSummaryQuery(DatasetFilterQuery):
    summaries: dict[ColumnKey, SummaryFunction] = Field(min_length=1, max_length=100)


DatasetPermission = Literal["read", "write", "read_write"]


class DatasetGrantInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    permission: DatasetPermission
    allow_delete: bool = False


class DatasetTokenInput(DatasetGrantInput):
    name: Annotated[str, Field(min_length=1, max_length=80)]



class DatasetConnectedInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: Literal[1]
    operation: Literal["find_rows", "get_row", "insert_row", "upsert_row", "delete_row"]
    columns: list[DatasetFieldContract] = Field(min_length=1, max_length=100)
    fields: list[ColumnKey] = Field(max_length=100)  # empty only for Insert and Upsert: identifiers only
    arguments: dict = Field(default_factory=dict, max_length=10)
    operation_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.:-]{1,128}$")


class DatasetCsvInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    text: str = Field(max_length=1_048_576)
    dataset_id: str | None = Field(default=None, min_length=1, max_length=100)
    schema_revision: int | None = Field(default=None, ge=1)
    create: DatasetCreate | None = None
    mapping: list[ColumnKey | None] | None = Field(default=None, max_length=100)
