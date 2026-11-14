"""Portable validation and normalization for Dataset column values."""
import json
import math
import re
from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Literal, TypeAlias, get_args
from urllib.parse import urlsplit

from .errors import AppError

ColumnKind: TypeAlias = Literal["text", "number", "boolean", "date", "datetime", "email", "select", "long_text", "url", "created_time", "updated_time", "multi_select", "auto_number"]
CellValue: TypeAlias = str | int | float | bool | None
DatasetValue: TypeAlias = CellValue | list[str]
FilterOperator: TypeAlias = Literal["eq", "ne", "lt", "lte", "gt", "gte", "contains", "is_null", "not_null", "in", "not_in", "not_contains", "contains_any", "contains_all"]
SummaryFunction: TypeAlias = Literal["count", "empty_count", "empty_percent", "unique_count", "sum", "avg", "min", "max"]
MAX_AGGREGATE_GROUPS = 20
SUMMARY_FUNCTIONS = ("count", "empty_count", "empty_percent", "unique_count")


def summary_functions(kind: ColumnKind) -> tuple[str, ...]:
    if kind in {"number", "auto_number"}:
        return (*SUMMARY_FUNCTIONS, "sum", "avg", "min", "max")
    if kind == "date" or kind in DATETIME_KINDS:
        return (*SUMMARY_FUNCTIONS, "min", "max")
    return SUMMARY_FUNCTIONS


FILTER_OPERATORS = get_args(FilterOperator)
TEXT_KINDS = frozenset({"text", "long_text", "url", "email", "select"})
SYSTEM_TIME_KINDS = frozenset({"created_time", "updated_time"})
READ_ONLY_KINDS = SYSTEM_TIME_KINDS | {"auto_number"}
DATETIME_KINDS = SYSTEM_TIME_KINDS | {"datetime"}
TEXT_FOLD_FUNCTION = "dataset_text_fold"


def dataset_timestamp(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def timestamp_millis(value: str) -> int:
    value = datetime.fromisoformat(value)
    delta = value - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return (delta.days * 86_400 + delta.seconds) * 1000 + delta.microseconds // 1000


def valid_url(value: str) -> bool:
    if len(value) > 2048 or re.search(r"[\s\x00-\x1f\x7f\\]", value):
        return False
    try:
        parts = urlsplit(value)
        parts.port  # Invalid numeric ports raise ValueError.
        return parts.scheme in {"http", "https"} and bool(parts.hostname) and parts.username is None
    except ValueError:
        return False


def fold_text(value: object) -> object:
    """The case fold that SQLite registers for search, contains and text sort; PostgreSQL uses `lower`."""
    return value.lower() if isinstance(value, str) else value


def filter_operators(kind: ColumnKind) -> tuple[str, ...]:
    if kind == "boolean":
        return ("eq", "ne", "is_null", "not_null", "in", "not_in")
    if kind == "multi_select":
        return ("contains_any", "contains_all", "is_null")
    return tuple(op for op in FILTER_OPERATORS if op not in {"contains_any", "contains_all"}
                 and (op not in {"contains", "not_contains"} or kind in TEXT_KINDS))

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


def normalize_cell(key: str, kind: ColumnKind, value: DatasetValue, options: list[str], *, required: bool) -> DatasetValue:
    if value is None and not required:
        return None
    if kind == "boolean" and type(value) is bool:
        return value
    if kind == "multi_select" and isinstance(value, list) and all(isinstance(item, str) and item in options for item in value):
        if not value and not required:
            return None
        if value and len(value) <= len(options) and len(value) == len(set(value)):
            selected = set(value)
            return [option for option in options if option in selected]
    if kind == "auto_number" and type(value) is int and 1 <= value <= MAX_SAFE_INTEGER:
        return value
    if kind == "number" and type(value) in (int, float):
        if -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER and math.isfinite(value):
            return value
    if isinstance(value, str) and not INVALID_TEXT.search(value):
        if kind in {"text", "long_text"} and len(value) <= MAX_TEXT:
            return value
        if kind == "select" and value in options:
            return value
        if kind == "email" and len(value.strip()) <= 254 and EMAIL.fullmatch(value.strip()):
            return value.strip().lower()
        if kind == "url" and valid_url(value):
            return value
        if kind == "date" or kind in DATETIME_KINDS:
            try:
                if kind == "date" and DATE.fullmatch(value):
                    return date.fromisoformat(value).isoformat()
                if kind in DATETIME_KINDS and DATETIME.fullmatch(value):
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
