"""Portable validation and normalization for Dataset column values."""
import json
import math
import re
from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Literal, TypeAlias, get_args

from .errors import AppError

ColumnKind: TypeAlias = Literal["text", "number", "boolean", "date", "datetime", "email", "select"]
CellValue: TypeAlias = str | int | float | bool | None
FilterOperator: TypeAlias = Literal["eq", "ne", "lt", "lte", "gt", "gte", "contains", "is_null", "not_null", "in", "not_in", "not_contains"]
SummaryFunction: TypeAlias = Literal["count", "empty_count", "empty_percent", "unique_count", "sum", "avg", "min", "max"]
MAX_AGGREGATE_GROUPS = 20
SUMMARY_FUNCTIONS = ("count", "empty_count", "empty_percent", "unique_count")


def summary_functions(kind: ColumnKind) -> tuple[str, ...]:
    if kind == "number":
        return (*SUMMARY_FUNCTIONS, "sum", "avg", "min", "max")
    if kind in {"date", "datetime"}:
        return (*SUMMARY_FUNCTIONS, "min", "max")
    return SUMMARY_FUNCTIONS


FILTER_OPERATORS = get_args(FilterOperator)
TEXT_KINDS = frozenset({"text", "email", "select"})
TEXT_FOLD_FUNCTION = "dataset_text_fold"


def fold_text(value: object) -> object:
    """The case fold that SQLite registers for search, contains and text sort; PostgreSQL uses `lower`."""
    return value.lower() if isinstance(value, str) else value


def filter_operators(kind: ColumnKind) -> tuple[str, ...]:
    if kind == "boolean":
        return ("eq", "ne", "is_null", "not_null", "in", "not_in")
    return tuple(op for op in FILTER_OPERATORS if op not in {"contains", "not_contains"} or kind in TEXT_KINDS)

COLUMN_KEY_PATTERN = r"^[a-z][a-z0-9_]{0,62}$"
MAX_ROW_BYTES = 65_536
MAX_PAGE_BYTES = 1_048_576
MAX_TEXT = 16_384
MAX_SAFE_INTEGER = (1 << 53) - 1
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
DATETIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,3})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)
INVALID_TEXT = re.compile(r"[\x00\ud800-\udfff]")
EMAIL = re.compile(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+")


def normalize_cell(key: str, kind: ColumnKind, value: CellValue, options: list[str], *, required: bool) -> CellValue:
    if value is None and not required:
        return None
    if kind == "boolean" and type(value) is bool:
        return value
    if kind == "number" and type(value) in (int, float):
        if -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER and math.isfinite(value):
            return value
    if isinstance(value, str) and not INVALID_TEXT.search(value):
        if kind == "text" and len(value) <= MAX_TEXT:
            return value
        if kind == "select" and value in options:
            return value
        if kind == "email" and len(value.strip()) <= 254 and EMAIL.fullmatch(value.strip()):
            return value.strip().lower()
        if kind in ("date", "datetime"):
            try:
                if kind == "date" and DATE.fullmatch(value):
                    return date.fromisoformat(value).isoformat()
                if kind == "datetime" and DATETIME.fullmatch(value):
                    utc = datetime.fromisoformat(value).astimezone(timezone.utc)
                    return utc.isoformat(timespec="milliseconds").replace("+00:00", "Z")
            except (ValueError, OverflowError):
                pass
    raise AppError("DATASET_VALUE_INVALID", field=key, kind=kind)


MAX_DATASET_ROWS = 25_000
SNAPSHOT_MAX_ROWS = 1_000


def key_digest(value: CellValue) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return sha256(json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()


def write_fingerprint(data: object) -> str:
    encoded = json.dumps(data, ensure_ascii=True, separators=(",", ":"), sort_keys=True, allow_nan=False)
    return sha256(encoded.encode()).hexdigest()


def dataset_size(payload: dict) -> int:
    return len(json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode())
