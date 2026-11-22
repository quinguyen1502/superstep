from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..core.dataset_types import MAX_COLUMNS, MAX_DATASET_ROWS
from .dataset import ColumnKey, DatasetFilterGroup, DatasetFilterQuery, Label


class DatasetShareInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: Label
    fields: list[ColumnKey] = Field(min_length=1, max_length=MAX_COLUMNS)
    filter_tree: DatasetFilterGroup | None = None
    schema_revision: int = Field(ge=1)

    @field_validator("filter_tree", mode="before")
    @classmethod
    def bound_tree(cls, tree):
        return DatasetFilterQuery.bound_tree(tree)

    @field_validator("fields")
    @classmethod
    def distinct_fields(cls, fields):
        if len(set(fields)) != len(fields):
            raise ValueError("Choose each field only once")
        return fields


class DatasetSharePagination(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=MAX_DATASET_ROWS)


class DatasetSharePage(DatasetSharePagination):
    search: str | None = Field(default=None, max_length=120)


class DatasetSharePreview(DatasetShareInput, DatasetSharePage):
    model_config = ConfigDict(extra="forbid", strict=True)
