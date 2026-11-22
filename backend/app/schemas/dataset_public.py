"""OpenAPI models for the existing Dataset Connected v1 wire contract.

The route keeps using DatasetConnectedInput and the service validators at runtime.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from ..core.dataset_types import MAX_AGGREGATE_GROUPS, CellValue
from .dataset import (
    ColumnKey,
    DatasetAggregateQuery,
    DatasetConnectedColumn,
    DatasetFilterQuery,
    DatasetSort,
    RowValues,
)
from .envelope import Envelope

RowId = Annotated[str, Field(min_length=1, max_length=100)]
OperationId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:-]{1,128}$")]
Fields = Annotated[list[ColumnKey], Field(min_length=1, max_length=100, json_schema_extra={"uniqueItems": True})]
WriteFields = Annotated[list[ColumnKey], Field(max_length=100, json_schema_extra={"uniqueItems": True})]


class DatasetConnectedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class DatasetFindArguments(DatasetFilterQuery):
    sorts: list[DatasetSort] = Field(default_factory=list, max_length=12)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=25_000)


class DatasetRowTarget(DatasetConnectedModel):
    row_id: RowId


class DatasetUniqueTarget(DatasetConnectedModel):
    key: ColumnKey
    value: str | int | float | bool


class DatasetInsertArguments(DatasetConnectedModel):
    values: RowValues


class DatasetUpsertArguments(DatasetInsertArguments):
    key: ColumnKey


class DatasetConnectedBinding(DatasetConnectedModel):
    version: Literal[1]
    columns: list[DatasetConnectedColumn] = Field(min_length=1, max_length=100)


class DatasetConnectedRead(DatasetConnectedBinding):
    fields: Fields
    operation_id: None = None


class DatasetConnectedWrite(DatasetConnectedBinding):
    fields: WriteFields
    operation_id: OperationId


class DatasetConnectedFind(DatasetConnectedRead):
    operation: Literal["find_rows"]
    arguments: DatasetFindArguments = Field(default_factory=DatasetFindArguments)


class DatasetConnectedAggregate(DatasetConnectedRead):
    operation: Literal["aggregate_rows"]
    arguments: DatasetAggregateQuery


class DatasetConnectedGet(DatasetConnectedRead):
    operation: Literal["get_row"]
    arguments: DatasetRowTarget


class DatasetConnectedInsert(DatasetConnectedWrite):
    operation: Literal["insert_row"]
    arguments: DatasetInsertArguments


class DatasetConnectedUpsert(DatasetConnectedWrite):
    operation: Literal["upsert_row"]
    arguments: DatasetUpsertArguments


class DatasetConnectedDelete(DatasetConnectedBinding):
    operation: Literal["delete_row"]
    fields: Fields
    operation_id: OperationId
    arguments: DatasetRowTarget | DatasetUniqueTarget


class DatasetConnectedRequest(RootModel[Annotated[
    DatasetConnectedFind | DatasetConnectedAggregate | DatasetConnectedGet
    | DatasetConnectedInsert | DatasetConnectedUpsert | DatasetConnectedDelete,
    Field(discriminator="operation"),
]]):
    pass


class DatasetRowIdentity(DatasetConnectedModel):
    id: RowId
    revision: int


class DatasetConnectedRow(DatasetRowIdentity):
    created: float = Field(description="Row creation time as Unix seconds.")
    updated: float = Field(description="Row update time as Unix seconds.")
    values: RowValues
    formula_errors: dict[ColumnKey, str] = Field(default_factory=dict)


class DatasetFindResult(DatasetConnectedModel):
    items: list[DatasetConnectedRow]
    next_offset: int | None
    schema_revision: int


class DatasetAggregateGroup(DatasetConnectedModel):
    group: CellValue
    total: int
    values: dict[ColumnKey, CellValue]


class DatasetAggregateResult(DatasetConnectedModel):
    group_by: ColumnKey | None
    groups: list[DatasetAggregateGroup] = Field(max_length=MAX_AGGREGATE_GROUPS)
    truncated: bool


class DatasetWriteResult(DatasetConnectedModel):
    row: DatasetConnectedRow | DatasetRowIdentity
    inserted: bool


class DatasetDeleteResult(DatasetConnectedModel):
    row_id: RowId
    deleted: Literal[True]


class DatasetConnectedEnvelope(Envelope[
    DatasetFindResult | DatasetAggregateResult | DatasetConnectedRow | DatasetWriteResult | DatasetDeleteResult
]):
    pass
