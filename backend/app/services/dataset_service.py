from __future__ import annotations

from time import time
from uuid import uuid4

from ..core import permissions as P
from ..core.dataset_types import INVALID_TEXT, normalize_cell
from ..core.errors import AppError
from ..models.dataset import Dataset, DatasetColumn
from ..repositories.datasets import DatasetRepository
from .access import AccessService
from .audit_service import AuditService

MAX_COLUMNS = 100


def _label(value: str, field: str) -> str:
    label = value.strip()
    if not label or INVALID_TEXT.search(label):
        raise AppError("DATASET_DEFINITION_INVALID", field=field)
    return label


def _description(value: str | None) -> str | None:
    return _label(value, "description") if value and value.strip() else None


def _column(data: dict, position: int) -> DatasetColumn:
    key, kind = data["key"], data["kind"]
    if key in {"constructor", "prototype"}:
        raise AppError("DATASET_DEFINITION_INVALID", field=key)
    options = [_label(option, key) for option in data["options"]]
    if (kind == "select") != bool(options) or len(options) != len(set(options)):
        raise AppError("DATASET_DEFINITION_INVALID", field=key)
    return DatasetColumn(
        key=key, kind=kind, label=_label(data["label"], key), position=position,
        required=data["required"], unique=data["unique"], archived=False, options=options,
        default_value=normalize_cell(key, kind, data["default"], options, required=False),
    )


def _summary(dataset: Dataset) -> dict:
    return {
        "id": dataset.id, "name": dataset.name, "description": dataset.description,
        "owner_id": dataset.owner_id, "team_id": dataset.team_id, "revision": dataset.revision,
        "created": dataset.created, "updated": dataset.updated,
    }


def _detail(dataset: Dataset) -> dict:
    return {
        **_summary(dataset),
        "columns": [
            {"key": col.key, "label": col.label, "kind": col.kind, "required": col.required,
             "unique": col.unique, "default": col.default_value, "options": col.options}
            for col in dataset.columns if not col.archived
        ],
    }


class DatasetService:
    def __init__(self, repo: DatasetRepository, access: AccessService, audit: AuditService):
        self.repo, self.access, self.audit = repo, access, audit

    def definition(self, uid: str, dataset_id: str) -> Dataset:
        dataset = self.repo.get(uid, dataset_id)
        if dataset is None:
            raise AppError("DATASET_NOT_FOUND")
        return dataset

    def editable_definition(self, uid: str, dataset_id: str, revision: int | None) -> Dataset:
        dataset = self.definition(uid, dataset_id)
        self.access.require(uid, P.RESOURCES_MANAGE)
        if revision is not None and revision != dataset.revision:
            raise AppError("DATASET_SCHEMA_CONFLICT")
        return dataset

    def _save(self, uid: str, dataset: Dataset, action: str, *, require_empty: bool = False, **details) -> dict:
        dataset.updated = time()
        saved = self.repo.save(uid, dataset, dataset.revision, require_empty=require_empty)
        self.audit.record(uid, action, "dataset", dataset.id, **details)
        return _detail(saved)

    def list(self, uid: str, limit: int, offset: int) -> dict:
        datasets = self.repo.list(uid, limit + 1, offset)
        return {"items": [_summary(dataset) for dataset in datasets[:limit]],
                "next_offset": offset + limit if len(datasets) > limit else None}

    def get(self, uid: str, dataset_id: str) -> dict:
        return _detail(self.definition(uid, dataset_id))

    def prepare_create(self, uid: str, *, name: str, description: str | None, team_id: str | None, columns: list[dict]) -> Dataset:
        self.access.require(uid, P.RESOURCES_MANAGE)
        if team_id is not None and team_id not in self.access.teams.teams_of(uid):
            raise AppError("DATASET_NOT_FOUND")
        fields = [_column(data, i) for i, data in enumerate(columns)]
        keys = [field.key for field in fields]
        if len(set(keys)) != len(keys):
            raise AppError("DATASET_COLUMN_KEY_TAKEN")
        label = _label(name, "name")
        now = time()
        return Dataset(
            id=uuid4().hex, owner_id=uid if team_id is None else None, team_id=team_id,
            name=label, name_key=label.casefold(), description=_description(description),
            revision=1, created=now, updated=now, columns=fields,
        )

    def create(self, uid: str, *, name: str, description: str | None, team_id: str | None, columns: list[dict]) -> dict:
        dataset = self.repo.add(self.prepare_create(uid, name=name, description=description, team_id=team_id, columns=columns))
        self.audit.record(uid, "dataset.create", "dataset", dataset.id)
        return _detail(dataset)

    def update(self, uid: str, dataset_id: str, *, name: str, description: str | None, revision: int) -> dict:
        dataset = self.editable_definition(uid, dataset_id, revision)
        dataset.name = _label(name, "name")
        dataset.name_key = dataset.name.casefold()
        dataset.description = _description(description)
        return self._save(uid, dataset, "dataset.update")

    def delete(self, uid: str, dataset_id: str, revision: int | None) -> dict:
        dataset = self.editable_definition(uid, dataset_id, revision)
        self.repo.delete(uid, dataset.id, dataset.revision)
        self.audit.record(uid, "dataset.delete", "dataset", dataset.id)
        return {"ok": True}

    @staticmethod
    def _find_column(dataset: Dataset, key: str) -> DatasetColumn:
        for field in dataset.columns:
            if field.key == key and not field.archived:
                return field
        raise AppError("DATASET_COLUMN_NOT_FOUND")

    def add_column(self, uid: str, dataset_id: str, *, column: dict, revision: int) -> dict:
        dataset = self.editable_definition(uid, dataset_id, revision)
        if any(field.key == column["key"] for field in dataset.columns):
            raise AppError("DATASET_COLUMN_KEY_TAKEN")
        if len(dataset.columns) >= MAX_COLUMNS:
            raise AppError("DATASET_COLUMN_LIMIT", max=MAX_COLUMNS)
        field = _column(column, len(dataset.columns))
        dataset.columns.append(field)
        return self._save(uid, dataset, "dataset.column_add", require_empty=field.required, field=field.key)

    def update_column(self, uid: str, dataset_id: str, key: str, *, column: dict, revision: int) -> dict:
        dataset = self.editable_definition(uid, dataset_id, revision)
        field = self._find_column(dataset, key)
        proposed = _column(column, field.position)
        if (
            proposed.key != field.key or proposed.kind != field.kind
            or proposed.required != field.required or proposed.unique != field.unique
            or not set(field.options).issubset(proposed.options)
        ):
            raise AppError("DATASET_SCHEMA_INCOMPATIBLE", field=key)
        field.label = proposed.label
        field.options = proposed.options
        field.default_value = proposed.default_value
        return self._save(uid, dataset, "dataset.column_update", field=key)

    def remove_column(self, uid: str, dataset_id: str, key: str, revision: int | None) -> dict:
        dataset = self.editable_definition(uid, dataset_id, revision)
        field = self._find_column(dataset, key)
        field.archived = True
        return self._save(uid, dataset, "dataset.column_remove", field=key)
