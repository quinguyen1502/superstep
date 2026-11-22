"""Dataset Connected v1 wire types for Python 3.9 and later."""
from __future__ import annotations

from typing import Dict, List, Literal, Optional, TypedDict, Union

DatasetScalar = Union[str, int, float, bool, None]
DatasetValue = Union[DatasetScalar, List[str]]
DatasetValues = Dict[str, DatasetValue]
DatasetKind = Literal[
    "text", "number", "boolean", "date", "datetime", "email", "select", "long_text",
    "url", "created_time", "updated_time", "multi_select", "auto_number",
]
DatasetFilterOperator = Literal[
    "eq", "ne", "lt", "lte", "gt", "gte", "contains", "is_null", "not_null", "in", "not_in",
    "not_contains", "contains_any", "contains_all",
]
DatasetSummary = Literal["count", "empty_count", "empty_percent", "unique_count", "sum", "avg", "min", "max"]


class _FormulaOptions(TypedDict, total=False):
    version: Literal[1]


class DatasetFormula(_FormulaOptions):
    expression: str


class DatasetColumnRules(TypedDict, total=False):
    min_length: Optional[int]
    max_length: Optional[int]
    min: Union[int, float, str, None]
    max: Union[int, float, str, None]
    integer: Optional[bool]
    domains: Optional[List[str]]


class _ColumnOptions(TypedDict, total=False):
    required: bool
    unique: bool
    default: DatasetValue
    options: List[str]
    formula: Optional[DatasetFormula]
    validation_rules: Optional[DatasetColumnRules]


class DatasetColumn(_ColumnOptions):
    key: str
    kind: DatasetKind


class _FilterOptions(TypedDict, total=False):
    value: Union[DatasetScalar, List[DatasetScalar]]


class DatasetFilter(_FilterOptions):
    field: str
    op: DatasetFilterOperator


class DatasetFilterRule(DatasetFilter):
    type: Literal["rule"]


class DatasetFilterGroup(TypedDict):
    type: Literal["group"]
    conjunction: Literal["and", "or"]
    children: List[Union[DatasetFilterRule, DatasetFilterGroup]]


class _SortOptions(TypedDict, total=False):
    descending: bool


class DatasetSort(_SortOptions):
    field: str


class _QueryFilters(TypedDict, total=False):
    filters: List[DatasetFilter]
    filter_mode: Literal["and", "or"]
    filter_tree: Optional[DatasetFilterGroup]
    search: Optional[str]


class DatasetFindArguments(_QueryFilters, total=False):
    sorts: List[DatasetSort]
    limit: int
    offset: int


class _AggregateOptions(_QueryFilters, total=False):
    group_by: Optional[str]


class DatasetAggregateArguments(_AggregateOptions):
    summaries: Dict[str, DatasetSummary]


class DatasetRowTarget(TypedDict):
    row_id: str


class DatasetUniqueTarget(TypedDict):
    key: str
    value: Union[str, int, float, bool]


DatasetDeleteTarget = Union[DatasetRowTarget, DatasetUniqueTarget]


class DatasetRowIdentity(TypedDict):
    id: str
    revision: int


class _RowDiagnostics(TypedDict, total=False):
    formula_errors: Dict[str, str]


class DatasetRow(DatasetRowIdentity, _RowDiagnostics):
    created: float
    updated: float
    values: DatasetValues


class DatasetFindResult(TypedDict):
    items: List[DatasetRow]
    next_offset: Optional[int]
    schema_revision: int


class DatasetAggregateGroup(TypedDict):
    group: DatasetScalar
    total: int
    values: Dict[str, DatasetScalar]


class DatasetAggregateResult(TypedDict):
    group_by: Optional[str]
    groups: List[DatasetAggregateGroup]
    truncated: bool


class DatasetWriteResult(TypedDict):
    row: Union[DatasetRow, DatasetRowIdentity]
    inserted: bool


class DatasetDeleteResult(TypedDict):
    row_id: str
    deleted: Literal[True]
