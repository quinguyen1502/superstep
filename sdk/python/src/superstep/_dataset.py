"""Sync and async clients for the Dataset Connected API."""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Optional, Sequence
from uuid import uuid4

import httpx

from ._base import DEFAULT_TIMEOUT, unwrap
from ._errors import APIConnectionError, ConfigError
from ._dataset_models import (
    DatasetAggregateArguments, DatasetAggregateResult, DatasetColumn, DatasetDeleteResult,
    DatasetDeleteTarget, DatasetFindArguments, DatasetFindResult, DatasetRow, DatasetValues, DatasetWriteResult,
)
from ._version import __version__

_RETRY_STATUS = {502, 503, 504}


def _connection_url(base_url: str, dataset_id: str) -> str:
    try:
        base = httpx.URL(base_url)
    except (httpx.InvalidURL, TypeError) as exc:
        raise ConfigError("Invalid Dataset base_url", code="CONFIG_INVALID") from exc
    if base.scheme not in ("http", "https") or not base.host or base.userinfo or base.query or base.fragment:
        raise ConfigError("Dataset base_url must be an HTTP(S) URL without credentials, query or fragment", code="CONFIG_INVALID")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", dataset_id):
        raise ConfigError("Invalid dataset_id", code="CONFIG_INVALID")
    origin = str(base).split('?', 1)[0].split('#', 1)[0].rstrip('/')
    return f"{origin}/api/datasets/{dataset_id}/connected"


def _response_data(response: httpx.Response) -> Any:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    return unwrap(response.status_code, dict(response.headers), payload)


class _DatasetConnection:
    def __init__(self, *, base_url: str, dataset_id: str, token: str, columns: Sequence[DatasetColumn]):
        if not token or not columns:
            raise ConfigError("Dataset clients require a token and column binding", code="CONFIG_MISSING")
        self._url = _connection_url(base_url, dataset_id)
        self._columns = list(columns)
        self._headers = {
            "Authorization": f"Bearer {token}", "Accept": "application/json",
            "Content-Type": "application/json", "User-Agent": f"superstep-python/{__version__}",
        }

    def _request(self, content: bytes) -> httpx.Request:
        # Use only Dataset credentials, even with a shared HTTP transport.
        return httpx.Request("POST", self._url, content=content, headers=self._headers)

    def _body(self, operation: str, fields: Sequence[str], arguments: Mapping[str, Any],
              operation_id: Optional[str] = None) -> bytes:
        payload = {"version": 1, "operation": operation, "columns": self._columns,
                   "fields": list(fields), "arguments": arguments}
        if operation in ("insert_row", "upsert_row", "delete_row"):
            payload["operation_id"] = uuid4().hex if operation_id is None else operation_id
        # Serialize once so a retry uses the same arguments and receipt identity.
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


class DatasetClient(_DatasetConnection):
    """Synchronous client with a Dataset API token and an explicit column binding."""

    def __init__(self, *, base_url: str, dataset_id: str, token: str, columns: Sequence[DatasetColumn],
                 timeout: float = DEFAULT_TIMEOUT, http_client: Optional[httpx.Client] = None):
        super().__init__(base_url=base_url, dataset_id=dataset_id, token=token, columns=columns)
        self._http = http_client if http_client is not None else httpx.Client(timeout=timeout)
        self._owns_http = http_client is None

    def _send(self, operation: str, fields: Sequence[str], arguments: Mapping[str, Any],
              operation_id: Optional[str] = None) -> Any:
        content = self._body(operation, fields, arguments, operation_id)
        for attempt in range(2):
            try:
                response = self._http.send(self._request(content), auth=None, follow_redirects=False)
            except (httpx.TransportError, httpx.DecodingError) as exc:
                if attempt:
                    raise APIConnectionError(str(exc) or type(exc).__name__, code="CONNECTION_ERROR") from exc
                continue
            if attempt or response.status_code not in _RETRY_STATUS:
                return _response_data(response)

    def find_rows(self, fields: Sequence[str], arguments: Optional[DatasetFindArguments] = None) -> DatasetFindResult:
        return self._send("find_rows", fields, arguments if arguments is not None else {})

    def get_row(self, row_id: str, fields: Sequence[str]) -> DatasetRow:
        return self._send("get_row", fields, {"row_id": row_id})

    def aggregate_rows(self, fields: Sequence[str], arguments: DatasetAggregateArguments) -> DatasetAggregateResult:
        return self._send("aggregate_rows", fields, arguments)

    def insert_row(self, values: DatasetValues, *, fields: Sequence[str] = (),
                   operation_id: Optional[str] = None) -> DatasetWriteResult:
        return self._send("insert_row", fields, {"values": values}, operation_id)

    def upsert_row(self, key: str, values: DatasetValues, *, fields: Sequence[str] = (),
                   operation_id: Optional[str] = None) -> DatasetWriteResult:
        return self._send("upsert_row", fields, {"key": key, "values": values}, operation_id)

    def delete_row(self, target: DatasetDeleteTarget, fields: Sequence[str], *,
                   operation_id: Optional[str] = None) -> DatasetDeleteResult:
        return self._send("delete_row", fields, target, operation_id)

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> DatasetClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


class AsyncDatasetClient(_DatasetConnection):
    """Asynchronous DatasetClient with the same operations and credential scope."""

    def __init__(self, *, base_url: str, dataset_id: str, token: str, columns: Sequence[DatasetColumn],
                 timeout: float = DEFAULT_TIMEOUT, http_client: Optional[httpx.AsyncClient] = None):
        super().__init__(base_url=base_url, dataset_id=dataset_id, token=token, columns=columns)
        self._http = http_client if http_client is not None else httpx.AsyncClient(timeout=timeout)
        self._owns_http = http_client is None

    async def _send(self, operation: str, fields: Sequence[str], arguments: Mapping[str, Any],
                    operation_id: Optional[str] = None) -> Any:
        content = self._body(operation, fields, arguments, operation_id)
        for attempt in range(2):
            try:
                response = await self._http.send(self._request(content), auth=None, follow_redirects=False)
            except (httpx.TransportError, httpx.DecodingError) as exc:
                if attempt:
                    raise APIConnectionError(str(exc) or type(exc).__name__, code="CONNECTION_ERROR") from exc
                continue
            if attempt or response.status_code not in _RETRY_STATUS:
                return _response_data(response)

    async def find_rows(self, fields: Sequence[str], arguments: Optional[DatasetFindArguments] = None) -> DatasetFindResult:
        return await self._send("find_rows", fields, arguments if arguments is not None else {})

    async def get_row(self, row_id: str, fields: Sequence[str]) -> DatasetRow:
        return await self._send("get_row", fields, {"row_id": row_id})

    async def aggregate_rows(self, fields: Sequence[str], arguments: DatasetAggregateArguments) -> DatasetAggregateResult:
        return await self._send("aggregate_rows", fields, arguments)

    async def insert_row(self, values: DatasetValues, *, fields: Sequence[str] = (),
                         operation_id: Optional[str] = None) -> DatasetWriteResult:
        return await self._send("insert_row", fields, {"values": values}, operation_id)

    async def upsert_row(self, key: str, values: DatasetValues, *, fields: Sequence[str] = (),
                         operation_id: Optional[str] = None) -> DatasetWriteResult:
        return await self._send("upsert_row", fields, {"key": key, "values": values}, operation_id)

    async def delete_row(self, target: DatasetDeleteTarget, fields: Sequence[str], *,
                         operation_id: Optional[str] = None) -> DatasetDeleteResult:
        return await self._send("delete_row", fields, target, operation_id)

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> AsyncDatasetClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()
