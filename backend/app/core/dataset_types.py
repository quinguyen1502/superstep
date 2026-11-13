"""Portable validation and normalization for Dataset column values."""
import math
import re
from datetime import date, datetime, timezone
from typing import Literal, TypeAlias

from .errors import AppError

ColumnKind: TypeAlias = Literal["text", "number", "boolean", "date", "datetime", "email", "select"]
CellValue: TypeAlias = str | int | float | bool | None

MAX_TEXT = 16_384
MAX_SAFE_INTEGER = (1 << 53) - 1
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
DATETIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,3})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])"
)
EMAIL = re.compile(r"[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+")


def normalize_cell(key: str, kind: ColumnKind, value: CellValue, options: list[str], *, required: bool) -> CellValue:
    if value is None and not required:
        return None
    if kind == "boolean" and type(value) is bool:
        return value
    if kind == "number" and type(value) in (int, float):
        if -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER and math.isfinite(value):
            return value
    if isinstance(value, str) and "\0" not in value:
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
