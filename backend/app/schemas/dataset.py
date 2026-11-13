from typing import Annotated

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
