"""Manager-owned Dataset projections and their anonymous read boundary."""

from __future__ import annotations

from asyncio import to_thread
from dataclasses import dataclass
from json import dumps
from secrets import token_urlsafe
from time import time
from uuid import uuid4

from ..core import config
from ..core.dataset_filters import tree_rules
from ..core.dataset_shares import DATASET_SHARE_PREFIX, DATASET_SHARE_TOKEN
from ..core.dataset_types import INVALID_TEXT, MAX_PAGE_BYTES, TEXT_KINDS, dataset_size
from ..core.errors import AppError
from ..models.dataset import Dataset, DatasetColumn
from ..models.dataset_share import DatasetShare
from ..repositories.dataset_rows import DatasetRowRepository, RowFilter, RowFilterGroup
from ..repositories.dataset_shares import DatasetShareRepository
from .dataset_rows import _active_columns, _query_predicates
from .dataset_service import DatasetService
from .pat_service import digest
from .rate_limit import RateLimiter

PUBLIC_KINDS = {
    "text", "long_text", "url", "email", "select", "number", "boolean", "date", "datetime",
    "created_time", "updated_time", "multi_select", "auto_number",
}
RATE_WINDOW = 60


def _signature(column: DatasetColumn | None) -> dict | None:
    if column is None or column.kind not in PUBLIC_KINDS:
        return None
    return {
        "kind": column.kind,
        "formula": digest(dumps(column.formula, sort_keys=True)) if column.formula else None,
    }


def _capture_schema(dataset: Dataset, columns: dict[str, DatasetColumn], fields: list[str], filter_tree: dict | None) -> dict:
    pending = list(fields)
    if filter_tree is not None:
        pending.extend(rule["field"] for _, rule in tree_rules(filter_tree))
    signatures = {}
    formulas = None
    while pending:
        key = pending.pop()
        if key in signatures:
            continue
        column = columns.get(key)
        signature = _signature(column)
        if signature is None:
            raise AppError("DATASET_SHARE_FIELD_UNAVAILABLE", field=key)
        signatures[key] = signature
        if column.formula:
            if formulas is None:
                formulas = dataset.compile_formulas()
            pending.extend(formulas[key].dependencies)
    return signatures


def _matches_schema(share: DatasetShare, columns: dict[str, DatasetColumn]) -> bool:
    return all(_signature(columns.get(key)) == expected for key, expected in share.schema_signature.items())


def _management_item(share: DatasetShare, columns: dict[str, DatasetColumn]) -> dict:
    return {
        "id": share.id, "name": share.name, "fields": share.fields, "filter_tree": share.filter_tree,
        "created": share.created, "updated": share.updated, "available": _matches_schema(share, columns),
    }


@dataclass(frozen=True)
class SharedView:
    dataset_id: str
    revision: int
    name: str
    columns: list[DatasetColumn]
    predicates: list[RowFilter | RowFilterGroup]

    def metadata(self) -> dict:
        return {
            "name": self.name,
            "columns": [{"key": column.key, "label": column.label, "kind": column.kind} for column in self.columns],
            "searchable": any(column.kind in TEXT_KINDS for column in self.columns),
        }


@dataclass(frozen=True)
class PublicRead:
    view: SharedView
    token_hash: str


def _share_name(name: str) -> str:
    name = name.strip()
    if not name or INVALID_TEXT.search(name):
        raise AppError("BAD_REQUEST")
    return name


def _view(dataset: Dataset, columns: dict[str, DatasetColumn], name: str, fields: list[str], filter_tree: dict | None) -> SharedView:
    predicates, _ = _query_predicates(columns, [], filter_tree, None)
    return SharedView(dataset.id, dataset.revision, name, [columns[key] for key in fields], predicates)


class DatasetShareService:
    def __init__(self, datasets: DatasetService, shares: DatasetShareRepository, rows: DatasetRowRepository, limiter: RateLimiter):
        self.datasets, self.shares, self.rows, self.limiter = datasets, shares, rows, limiter

    def list(self, uid: str, dataset_id: str, limit: int, offset: int) -> dict:
        dataset = self.datasets.managed_definition(uid, dataset_id, None)
        columns = _active_columns(dataset)
        shares = self.shares.list(dataset.id, limit + 1, offset)
        return {
            "items": [_management_item(share, columns) for share in shares[:limit]],
            "next_offset": offset + limit if len(shares) > limit else None,
        }

    def create(self, uid: str, dataset_id: str, *, name: str, fields: list[str], filter_tree: dict | None, schema_revision: int) -> dict:
        dataset = self.datasets.managed_definition(uid, dataset_id, schema_revision)
        columns = _active_columns(dataset)
        name = _share_name(name)
        signature = _capture_schema(dataset, columns, fields, filter_tree)
        _query_predicates(columns, [], filter_tree, None)
        token = DATASET_SHARE_PREFIX + token_urlsafe(32)
        now = time()
        share = DatasetShare(
            id=uuid4().hex, dataset_id=dataset.id, name=name, fields=fields, filter_tree=filter_tree,
            schema_signature=signature, token_hash=digest(token), created=now, updated=now,
        )
        self.shares.add(uid, dataset, share)
        self._audit(uid, share, "create")
        return {**_management_item(share, columns), "token": token}

    def rotate(self, uid: str, dataset_id: str, share_id: str) -> dict:
        dataset = self.datasets.managed_definition(uid, dataset_id, None)
        columns = _active_columns(dataset)
        share = self.shares.get(dataset.id, share_id)
        if not _matches_schema(share, columns):
            raise AppError("DATASET_SHARE_SCHEMA_CHANGED")
        token = DATASET_SHARE_PREFIX + token_urlsafe(32)
        share = self.shares.change(uid, dataset, share_id, token_hash=digest(token), updated=time())
        self._audit(uid, share, "rotate")
        return {**_management_item(share, columns), "token": token}

    def revoke(self, uid: str, dataset_id: str, share_id: str) -> dict:
        dataset = self.datasets.managed_definition(uid, dataset_id, None)
        now = time()
        share = self.shares.change(uid, dataset, share_id, revoked=now, updated=now)
        self._audit(uid, share, "revoke")
        return {"ok": True}

    def _audit(self, uid: str, share: DatasetShare, operation: str) -> None:
        self.datasets.audit.record(uid, f"share.dataset_{operation}", "dataset_share", share.id, dataset_id=share.dataset_id)

    def preview(self, uid: str, dataset_id: str, *, name: str, fields: list[str], filter_tree: dict | None,
                schema_revision: int, search: str | None, limit: int, offset: int) -> dict:
        dataset = self.datasets.managed_definition(uid, dataset_id, schema_revision)
        columns = _active_columns(dataset)
        _capture_schema(dataset, columns, fields, filter_tree)
        view = _view(dataset, columns, _share_name(name), fields, filter_tree)
        page = self._page(view, search, limit, offset)
        if self.datasets.revisions(uid, dataset.id)["schema_revision"] != view.revision:
            raise AppError("DATASET_SCHEMA_CONFLICT")
        return {"view": view.metadata(), **page}

    async def _limit(self, key: str, limit: int) -> None:
        allowed, retry = await self.limiter.hit(key, limit, RATE_WINDOW)
        if not allowed:
            raise AppError("RATE_LIMITED", retry_after=retry, headers={"Retry-After": str(retry)})

    async def authorize(self, secret: str, ip: str) -> PublicRead:
        await self._limit(f"pubdataset-ip:{digest(ip)}", config.public_dataset_rate_ip())
        if not DATASET_SHARE_TOKEN.fullmatch(secret):
            raise AppError("DATASET_SHARE_NOT_FOUND")
        token_hash = digest(secret)
        found = await to_thread(self.shares.resolve, token_hash)
        if found is None:
            raise AppError("DATASET_SHARE_NOT_FOUND")
        share, dataset = found
        await self._limit(f"pubdataset-link:{share.id}", config.public_dataset_rate_link())
        columns = _active_columns(dataset)
        if not _matches_schema(share, columns):
            raise AppError("DATASET_SHARE_NOT_FOUND")
        try:
            view = _view(dataset, columns, share.name, share.fields, share.filter_tree)
        except AppError as exc:
            raise AppError("DATASET_SHARE_NOT_FOUND") from exc
        return PublicRead(view, token_hash)

    def read_rows(self, public: PublicRead, *, search: str | None, limit: int, offset: int) -> dict:
        page = self._page(public.view, search, limit, offset)
        # Reject a result built while its share rotated, was revoked or its schema changed.
        if not self.shares.is_current(public.view.dataset_id, public.view.revision, public.token_hash):
            raise AppError("DATASET_SHARE_NOT_FOUND")
        return page

    def _page(self, view: SharedView, search: str | None, limit: int, offset: int) -> dict:
        _, search_columns = _query_predicates({column.key: column for column in view.columns}, [], None, search)
        rows = self.rows.project_page(
            view.dataset_id, filters=view.predicates, search=search, search_columns=search_columns,
            columns=view.columns, limit=limit + 1, offset=offset,
        )
        items = []
        remaining = MAX_PAGE_BYTES
        for values in rows[:limit]:
            remaining -= dataset_size(values)
            if remaining < 0:
                break
            items.append(values)
        next_offset = offset + len(items) if len(items) < len(rows) else None
        return {"items": items, "next_offset": next_offset}
