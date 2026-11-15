"""Bounded CSV preview, atomic import and spreadsheet-safe export."""
import csv
import io
import re
from dataclasses import dataclass

from ..core import permissions as P
from ..core.dataset_types import INVALID_TEXT, MAX_ROW_BYTES, READ_ONLY_KINDS, DatasetValue, dataset_size, key_digest, normalize_cell
from ..core.errors import AppError
from ..models.dataset import DatasetColumn
from ..repositories.dataset_rows import DatasetRowRepository
from .dataset_rows import _row_values, _active_columns, _normalize
from .dataset_service import MAX_COLUMNS, DatasetService, _detail

MAX_CSV_BYTES = 1_048_576
MAX_CSV_RECORDS = 1_000
MAX_EXPORT_BYTES = 16_777_216
MAX_PREVIEW_ROWS = 20
MAX_ISSUES = 100
ISSUE_VALUE_CHARS = 200
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
TEXT_LIKE_NUMBER = re.compile(r"\+|-?0[0-9]")  # phone numbers, codes and IDs keep their leading `+` or zero
MAX_NUMBER_DIGITS = 15  # longer digit runs lose precision as a number
FORMULA_START = ("=", "+", "-", "@", "\uff1d", "\uff0b", "\uff0d", "\uff20")


def _guarded(value: str) -> bool:
    """True when export prefixes `'` so a spreadsheet does not run the value as a formula."""
    value = value.lstrip("'")  # a value that already starts with the guard keeps it on the way back
    return value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(FORMULA_START)


def unguard(value: str) -> str:
    """Remove the export formula guard so export then import gives the original value."""
    return value[1:] if value.startswith("'") and _guarded(value[1:]) else value


@dataclass
class CsvTable:
    headers: list[str]
    rows: list[tuple[int, list[str]]]


def parse_csv(text: str) -> CsvTable:
    if INVALID_TEXT.search(text):
        raise AppError("DATASET_CSV_INVALID", row=1)
    if len(text.encode("utf-8")) > MAX_CSV_BYTES:
        raise AppError("DATASET_CSV_LIMIT", max=MAX_CSV_BYTES)
    reader = csv.reader(io.StringIO(text.removeprefix("\ufeff"), newline=""), strict=True)
    rows = []
    line = 1
    try:
        headers = next(reader, [])
        headers = [unguard(header) for header in headers]
        if not headers or len(headers) > MAX_COLUMNS or any(not header.strip() for header in headers):
            raise AppError("DATASET_CSV_INVALID", row=1)
        line = reader.line_num + 1
        for record in reader:
            if record:
                rows.append((line, record))
                if len(rows) > MAX_CSV_RECORDS:
                    raise AppError("DATASET_CSV_RECORD_LIMIT", max=MAX_CSV_RECORDS)
            line = reader.line_num + 1
    except csv.Error as exc:
        raise AppError("DATASET_CSV_INVALID", row=line) from exc
    return CsvTable(headers, rows)


def _coerce(kind: str, text: str) -> DatasetValue:
    if kind == "multi_select":
        return text.split(";")
    if kind == "number" and NUMBER.fullmatch(text.strip()):
        return float(text)
    if kind == "boolean" and text.strip().lower() in {"true", "false", "1", "0"}:
        return text.strip().lower() in {"true", "1"}
    return text


def _matches(kind: str, value: str) -> bool:
    if kind == "number" and (TEXT_LIKE_NUMBER.match(value.strip())
                             or sum(char.isdigit() for char in value) > MAX_NUMBER_DIGITS):
        return False
    if kind == "boolean" and value.strip().lower() not in {"true", "false"}:
        return False
    try:
        normalize_cell("value", kind, _coerce(kind, value), [], required=True)
        return True
    except AppError:
        return False


def _suggest_columns(table: CsvTable) -> list[dict]:
    used = {"constructor", "prototype"}
    columns = []
    for index, header in enumerate(table.headers):
        base = re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")
        if not base or not base[0].isalpha():
            base = f"field_{base or index + 1}"
        base = base[:58]
        key, suffix = base, 2
        while key in used:
            key = f"{base}_{suffix}"
            suffix += 1
        used.add(key)
        values = [row[index] for _, row in table.rows if len(row) == len(table.headers) and row[index] != ""]
        kind = "text" if any(unguard(value) != value for value in values) else next(
            (kind for kind in ("boolean", "date", "datetime", "email", "number")
             if values and all(_matches(kind, value) for value in values)), "text")
        columns.append({"key": key, "label": header.strip()[:120], "kind": kind,
                        "required": False, "unique": False, "default": None, "options": []})
    return columns


def _suggest_mapping(headers: list[str], columns: list[DatasetColumn]) -> list[str | None]:
    by_key = {column.key.casefold(): column.key for column in columns}
    by_label: dict[str, list[str]] = {}
    for column in columns:
        by_label.setdefault(column.label.casefold(), []).append(column.key)
    used = set()
    mapping = []
    for header in headers:
        name = header.strip().casefold()
        labels = by_label.get(name, [])
        field = by_key.get(name) or (labels[0] if len(labels) == 1 else None)
        mapping.append(field if field not in used else None)
        if field is not None:
            used.add(field)
    return mapping


def _csv_value(value: DatasetValue) -> str | int | float:
    if isinstance(value, list):
        value = ";".join(value)
    if value is None:
        return ""
    if type(value) is bool:
        return "true" if value else "false"
    if isinstance(value, str) and _guarded(value):
        return "'" + value
    return value


class DatasetCsvService:
    def __init__(self, datasets: DatasetService, rows: DatasetRowRepository):
        self.datasets, self.rows = datasets, rows

    def _prepare(self, uid: str, *, text: str, dataset_id: str | None, schema_revision: int | None,
                 create: dict | None, mapping: list[str | None] | None, commit: bool):
        self.datasets.access.require(uid, P.RESOURCES_MANAGE)
        if (dataset_id is not None and create is not None) or (commit and dataset_id is None and create is None):
            raise AppError("DATASET_CSV_MAPPING_INVALID")
        if commit and dataset_id is not None and schema_revision is None:
            raise AppError("DATASET_SCHEMA_CONFLICT")
        dataset = self.datasets.editable_definition(uid, dataset_id, schema_revision) if dataset_id else None
        table = parse_csv(text)
        if not dataset:
            definition = create if create is not None else {
                "name": "CSV", "description": None, "team_id": None, "columns": _suggest_columns(table),
            }
            dataset = self.datasets.prepare_create(uid, **definition)
        columns = _active_columns(dataset)
        writable = {key: column for key, column in columns.items() if column.kind not in READ_ONLY_KINDS}
        if mapping is None:
            mapping = _suggest_mapping(table.headers, list(writable.values())) if dataset_id or create else list(columns)
        mapped = [key for key in mapping if key is not None]
        if len(mapping) != len(table.headers) or len(set(mapped)) != len(mapped) or set(mapped) - writable.keys() or (commit and not mapped):
            raise AppError("DATASET_CSV_MAPPING_INVALID")

        issues = []
        invalid_rows = set()
        records = []
        keys = {key: {} for key, column in writable.items() if column.unique}
        key_values = {}

        def issue(line: int, error: AppError, field: str | None = None, value: object = None):
            invalid_rows.add(line)
            if len(issues) < MAX_ISSUES:
                rejected = None if value is None else str(value)[:ISSUE_VALUE_CHARS]
                issues.append({"row": line, "field": field, "value": rejected, "error": error.to_dict()})

        for line, record in table.rows:
            if len(record) != len(table.headers):
                issue(line, AppError("DATASET_CSV_INVALID", row=line))
                continue
            incoming = {key: unguard(value) for key, value in zip(mapping, record) if key is not None and value != ""}
            values = {}
            for key, column in writable.items():
                try:
                    value = _coerce(column.kind, incoming[key]) if key in incoming else column.default_value
                    values[key] = _normalize(column, value)
                except AppError as exc:
                    issue(line, exc, key, incoming.get(key))
            if line in invalid_rows:
                continue
            if dataset_size(values) > MAX_ROW_BYTES:
                issue(line, AppError("DATASET_ROW_TOO_LARGE", max=MAX_ROW_BYTES))
                continue
            for field, hashes in keys.items():
                if values[field] is not None:
                    digest = key_digest(values[field])
                    key_values[field, line] = values[field]
                    if digest in hashes:
                        issue(line, AppError("DATASET_UNIQUE_CONFLICT"), field, values[field])
                    hashes.setdefault(digest, []).append(line)
            records.append(values)

        if dataset_id:
            for field, hashes in keys.items():
                for digest in self.rows.matching_keys(dataset.id, field, set(hashes)):
                    for line in hashes[digest]:
                        issue(line, AppError("DATASET_UNIQUE_CONFLICT"), field, key_values.get((field, line)))
        issues.sort(key=lambda item: item["row"])
        result = {
            "headers": table.headers, "columns": _detail(dataset)["columns"], "mapping": mapping,
            "schema_revision": dataset.revision if dataset_id else None, "total_rows": len(table.rows),
            "invalid_rows": len(invalid_rows), "issues": issues,
            "sample": [{"row": line, "cells": [unguard(cell)[:300] for cell in record[:MAX_COLUMNS]]}
                       for line, record in table.rows[:MAX_PREVIEW_ROWS]],
        }
        return dataset, records, result

    def preview(self, uid: str, **params) -> dict:
        return self._prepare(uid, **params, commit=False)[2]

    def import_csv(self, uid: str, **params) -> dict:
        dataset, values, preview = self._prepare(uid, **params, commit=True)
        if preview["invalid_rows"]:
            raise AppError("DATASET_CSV_ROWS_INVALID", details={"issues": preview["issues"]})
        create = params["dataset_id"] is None
        self.rows.import_rows(uid, dataset, values, create=create)
        if create:
            self.datasets.audit.record(uid, "dataset.create", "dataset", dataset.id)
        self.datasets.audit.record(uid, "dataset.csv_import", "dataset", dataset.id, rows=len(values))
        return {"dataset": _detail(dataset), "imported": len(values)}

    def export(self, uid: str, dataset_id: str) -> tuple[str, bytes]:
        dataset = self.datasets.definition(uid, dataset_id)
        columns = _active_columns(dataset)
        output = bytearray(b"\xef\xbb\xbf")
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer)
        def append(values):
            writer.writerow(values)
            output.extend(buffer.getvalue().encode("utf-8"))
            buffer.seek(0)
            buffer.truncate()
            if len(output) > MAX_EXPORT_BYTES:
                raise AppError("DATASET_CSV_LIMIT", max=MAX_EXPORT_BYTES)
        append(_csv_value(column.label) for column in columns.values())
        rows = self.rows.export_rows(uid, dataset.id)
        try:
            for row in rows:
                values = _row_values(row, columns)
                append(_csv_value(values[key]) for key in columns)
        finally:
            rows.close()
        return dataset.name, bytes(output)
