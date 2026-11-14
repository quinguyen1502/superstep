from __future__ import annotations

import json
from time import time
from uuid import uuid4

from ..core import permissions as P
from ..core.dataset_rules import column_display, column_rules, enforce_rules
from ..core.dataset_types import INVALID_TEXT, SYSTEM_TIME_KINDS, normalize_cell
from ..core.errors import AppError
from ..engine import dataset_nodes
from ..models.dataset import Dataset, DatasetColumn
from ..repositories.datasets import DatasetRepository, RowChange
from .access import AccessService
from .audit_service import AuditService

MAX_COLUMNS = 100
MAX_COLUMN_DEFINITIONS = 200  # active plus removed; a removed key stays reserved


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
    if ((kind in {"long_text", "multi_select"} and data["unique"])
            or (kind == "auto_number" and (data["required"] or data["default"] is not None))
            or (kind in SYSTEM_TIME_KINDS and (data["required"] or data["unique"] or data["default"] is not None))):
        raise AppError("DATASET_DEFINITION_INVALID", field=key)
    options = [_label(option, key) for option in data["options"]]
    if (kind in {"select", "multi_select"}) != bool(options) or len(options) != len(set(options)):
        raise AppError("DATASET_DEFINITION_INVALID", field=key)
    if kind == "multi_select" and any(";" in option for option in options):
        raise AppError("DATASET_DEFINITION_INVALID", field=key)
    rules = column_rules(key, kind, data.get("validation_rules"))
    display = column_display(key, kind, data.get("display_format"))
    default = normalize_cell(key, kind, data["default"], options, required=False)
    return DatasetColumn(
        key=key, kind=kind, label=_label(data["label"], key), position=position,
        required=data["required"], unique=data["unique"] or kind == "auto_number", archived=False, options=options,
        validation_rules=rules or None, display_format=display or None,
        default_value=enforce_rules(key, default, rules),
    )


def _matches_by(binding: dict, key: str) -> bool:
    """Whether a Dataset node or Agent tool binding finds its row by this unique field."""
    arguments = binding.get("arguments")
    if binding.get("operation") in {"upsert_row", "delete_row"} and isinstance(arguments, dict) and arguments.get("key") == key:
        return True
    operations = binding.get("operations")
    return isinstance(operations, list) and "upsert_row" in operations and binding.get("key") == key


def _summary(dataset: Dataset) -> dict:
    return {
        "id": dataset.id, "name": dataset.name, "description": dataset.description,
        "owner_id": dataset.owner_id, "team_id": dataset.team_id, "team_owner_id": dataset.team_owner_id,
        "revision": dataset.revision, "created": dataset.created, "updated": dataset.updated,
    }


def _detail(dataset: Dataset) -> dict:
    return {
        **_summary(dataset),
        "columns": [
            {"key": col.key, "label": col.label, "kind": col.kind, "required": col.required,
             "unique": col.unique, "default": col.default_value, "options": col.options,
             **({"validation_rules": col.validation_rules} if col.validation_rules else {}),
             **({"display_format": col.display_format} if col.display_format else {})}
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
        """A dataset whose rows the caller may add, edit, import, and delete."""
        dataset = self.definition(uid, dataset_id)
        self.access.require(uid, P.RESOURCES_MANAGE)
        if revision is not None and revision != dataset.revision:
            raise AppError("DATASET_SCHEMA_CONFLICT")
        return dataset

    def can_manage(self, uid: str, dataset: Dataset) -> bool:
        """Schema, dataset deletion, grants, and tokens: the personal owner, a team dataset's owner, or an admin."""
        if not self.access.can(uid, P.RESOURCES_MANAGE):
            return False
        if dataset.team_id is None:
            return dataset.owner_id == uid
        return dataset.team_owner_id == uid or self.access.can(uid, P.ORG_MANAGE)

    def managed_definition(self, uid: str, dataset_id: str, revision: int | None) -> Dataset:
        dataset = self.editable_definition(uid, dataset_id, None)
        if not self.can_manage(uid, dataset):
            raise AppError("DATASET_MANAGE_DENIED")
        if revision is not None and revision != dataset.revision:
            raise AppError("DATASET_SCHEMA_CONFLICT")
        return dataset

    def _save(self, uid: str, dataset: Dataset, action: str, *, require_empty: bool = False,
              unique_change: tuple[str, bool] | None = None, rows: RowChange | None = None, validate_field: str | None = None, **details) -> dict:
        dataset.updated = time()
        saved, changed = self.repo.save(uid, dataset, dataset.revision, require_empty=require_empty,
                                        unique=unique_change, rows=rows, validate_field=validate_field)
        if rows is not None:
            details["rows"] = changed
        self.audit.record(uid, action, "dataset", dataset.id, **details)
        return _detail(saved)

    def list(self, uid: str, limit: int, offset: int) -> dict:
        datasets = self.repo.list(uid, limit + 1, offset)
        return {"items": [_summary(dataset) for dataset in datasets[:limit]],
                "next_offset": offset + limit if len(datasets) > limit else None}

    def get(self, uid: str, dataset_id: str) -> dict:
        return _detail(self.definition(uid, dataset_id))

    def transfer(self, uid: str, dataset_id: str, *, user_id: str, revision: int) -> dict:
        """Admins hand a team dataset to another member of its team who can manage resources."""
        dataset = self.definition(uid, dataset_id)
        self.access.require(uid, P.ORG_MANAGE)
        if revision != dataset.revision:
            raise AppError("DATASET_SCHEMA_CONFLICT")
        if dataset.team_id is None or dataset.team_id not in self.access.teams.teams_of(user_id) \
                or not self.access.can(user_id, P.RESOURCES_MANAGE):
            raise AppError("DATASET_OWNER_INVALID")
        previous, dataset.team_owner_id = dataset.team_owner_id, user_id
        return self._save(uid, dataset, "dataset.transfer", from_user=previous, to_user=user_id)

    def prepare_create(self, uid: str, *, name: str, description: str | None, team_id: str | None, columns: list[dict]) -> Dataset:
        self.access.require(uid, P.RESOURCES_MANAGE)
        if team_id is not None and team_id not in self.access.teams.teams_of(uid):
            raise AppError("DATASET_TEAM_FORBIDDEN")
        fields = [_column(data, i) for i, data in enumerate(columns)]
        keys = [field.key for field in fields]
        if len(set(keys)) != len(keys):
            raise AppError("DATASET_COLUMN_KEY_TAKEN")
        label = _label(name, "name")
        now = time()
        return Dataset(
            id=uuid4().hex, owner_id=uid if team_id is None else None, team_id=team_id,
            team_owner_id=uid if team_id is not None else None,
            name=label, name_key=label.casefold(), description=_description(description),
            revision=1, created=now, updated=now, columns=fields,
        )

    def create(self, uid: str, *, name: str, description: str | None, team_id: str | None, columns: list[dict]) -> dict:
        dataset = self.repo.add(self.prepare_create(uid, name=name, description=description, team_id=team_id, columns=columns))
        self.audit.record(uid, "dataset.create", "dataset", dataset.id)
        return _detail(dataset)

    def update(self, uid: str, dataset_id: str, *, name: str, description: str | None, revision: int) -> dict:
        dataset = self.managed_definition(uid, dataset_id, revision)
        dataset.name = _label(name, "name")
        dataset.name_key = dataset.name.casefold()
        dataset.description = _description(description)
        return self._save(uid, dataset, "dataset.update")

    def delete(self, uid: str, dataset_id: str, revision: int) -> dict:
        dataset = self.managed_definition(uid, dataset_id, revision)
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
        dataset = self.managed_definition(uid, dataset_id, revision)
        if any(field.key == column["key"] for field in dataset.columns):
            raise AppError("DATASET_COLUMN_KEY_TAKEN")
        if sum(not field.archived for field in dataset.columns) >= MAX_COLUMNS:
            raise AppError("DATASET_COLUMN_LIMIT", max=MAX_COLUMNS)
        if len(dataset.columns) >= MAX_COLUMN_DEFINITIONS:
            raise AppError("DATASET_COLUMN_LIMIT", max=MAX_COLUMN_DEFINITIONS)
        field = _column(column, len(dataset.columns))
        dataset.columns.append(field)
        if field.kind == "auto_number":
            return self._save(uid, dataset, "dataset.column_add", rows=RowChange(field.key, auto_number=True),
                              unique_change=(field.key, True), field=field.key)
        if field.required and field.default_value is not None:
            # Existing rows take the default in the same transaction; a unique default fails on a second row.
            return self._save(uid, dataset, "dataset.column_add", rows=RowChange(field.key, value=field.default_value),
                              unique_change=(field.key, True) if field.unique else None, field=field.key)
        return self._save(uid, dataset, "dataset.column_add", require_empty=field.required, field=field.key)

    def update_column(self, uid: str, dataset_id: str, key: str, *, column: dict, revision: int) -> dict:
        dataset = self.managed_definition(uid, dataset_id, revision)
        field = self._find_column(dataset, key)
        proposed = _column(column, field.position)
        if (
            proposed.key != field.key or proposed.kind != field.kind or proposed.required != field.required
            or not set(field.options).issubset(proposed.options)
        ):
            raise AppError("DATASET_SCHEMA_INCOMPATIBLE", field=key)
        unique_change = None
        if proposed.unique != field.unique:
            if not proposed.unique:
                self._require_unbound_key(uid, dataset.id, key)
            unique_change = (key, proposed.unique)
        validate_field = key if proposed.validation_rules and proposed.validation_rules != field.validation_rules else None
        field.validation_rules = proposed.validation_rules
        field.display_format = proposed.display_format
        field.label = proposed.label
        field.options = proposed.options
        field.default_value = proposed.default_value
        field.unique = proposed.unique
        changes = {"unique": proposed.unique} if unique_change else {}
        return self._save(uid, dataset, "dataset.column_update", unique_change=unique_change, validate_field=validate_field, field=key, **changes)

    def _require_unbound_key(self, uid: str, dataset_id: str, key: str) -> None:
        """A field that a saved workflow uses to match rows (upsert or delete) must stay unique."""
        for workflow_id, name, data in self.repo.workflows_mentioning(dataset_id):
            try:
                graph = json.loads(data or "{}")
            except ValueError:
                continue
            for binding in dataset_nodes.bindings(graph if isinstance(graph, dict) else {}).values():
                if binding.get("dataset_id") == dataset_id and _matches_by(binding, key):
                    visible = self.access.may(workflow_id, uid)
                    raise AppError("DATASET_SCHEMA_INCOMPATIBLE", details={
                        "field": key, "workflow_id": workflow_id if visible else None,
                        "workflow": (name or workflow_id) if visible else None,
                    }, field=key)

    def remove_column(self, uid: str, dataset_id: str, key: str, revision: int) -> dict:
        dataset = self.managed_definition(uid, dataset_id, revision)
        field = self._find_column(dataset, key)
        field.archived = True
        dropped = (key, False) if field.unique else None
        return self._save(uid, dataset, "dataset.column_remove", rows=RowChange(key, clear=True), unique_change=dropped, field=key)
