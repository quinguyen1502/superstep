"""Dataset requests, response projection, and transport retries."""
import inspect
import json
from uuid import UUID

import httpx
import pytest

from superstep import APIConnectionError, AsyncDatasetClient, ConfigError, DatasetClient, PermissionDeniedError

OPTIONS = {
    "base_url": "https://example.com/studio/", "dataset_id": "tickets", "token": "dsat_example",
    "columns": [{"key": "subject", "kind": "text"}],
}


async def resolved(value):
    return await value if inspect.isawaitable(value) else value


@pytest.fixture(params=[False, True], ids=["sync", "async"])
async def connected(request):
    clients = []

    def create(handler):
        asynchronous = request.param
        http_type = httpx.AsyncClient if asynchronous else httpx.Client
        http = http_type(transport=httpx.MockTransport(handler), follow_redirects=True,
                         auth=("owner", "secret"), headers={"X-Workflow-Token": "wft_example"},
                         cookies={"session": "owner"}, params={"auth": "owner"})
        client = (AsyncDatasetClient if asynchronous else DatasetClient)(**OPTIONS, http_client=http)
        clients.append((http, client, asynchronous))
        return client

    yield create
    for http, client, asynchronous in clients:
        await resolved(client.aclose() if asynchronous else client.close())
        assert not http.is_closed
        await resolved(http.aclose() if asynchronous else http.close())


async def test_retry_keeps_the_original_body_and_new_write_has_a_new_id(connected):
    requests = []
    values = {"subject": "first"}

    def handle(request):
        assert request.method == "POST" and str(request.url) == "https://example.com/studio/api/datasets/tickets/connected"
        assert request.headers["Authorization"] == "Bearer dsat_example"
        assert "X-Workflow-Token" not in request.headers and "cookie" not in request.headers
        requests.append(request.content)
        if len(requests) == 1:
            values["subject"] = "second"
            raise httpx.ReadError("connection interrupted")
        return httpx.Response(200, json={"success": True, "data": {"row": {"id": "row", "revision": 1}, "inserted": True}})

    client = connected(handle)
    for _ in range(2):
        assert await resolved(client.insert_row(values)) == {"row": {"id": "row", "revision": 1}, "inserted": True}
    assert requests[0] == requests[1]
    first, second = json.loads(requests[0]), json.loads(requests[2])
    assert first["arguments"] == {"values": {"subject": "first"}}
    assert second["arguments"] == {"values": {"subject": "second"}}
    assert first["fields"] == [] and UUID(first["operation_id"]) != UUID(second["operation_id"])


async def test_transient_status_reads_and_server_error_details(connected):
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(503)
        return httpx.Response(403, json={"success": False, "error": {
            "code": "DATASET_TOKEN_SCOPE", "message": "Denied", "details": {"operation": "delete_row"},
        }})

    client = connected(handle)
    with pytest.raises(PermissionDeniedError) as exc:
        await resolved(client.delete_row({"key": "subject", "value": "abc"}, ["subject"], operation_id="job:delete"))
    assert (exc.value.code, exc.value.status, exc.value.details) == ("DATASET_TOKEN_SCOPE", 403, {"operation": "delete_row"})
    assert requests == [{
        "version": 1, "operation": "delete_row", "columns": OPTIONS["columns"], "fields": ["subject"],
        "arguments": {"key": "subject", "value": "abc"}, "operation_id": "job:delete",
    }] * 2


async def test_never_follows_redirects(connected):
    requests = []

    def handle(request):
        requests.append(request.url)
        return httpx.Response(307, headers={"Location": "https://other-origin.example/path"})

    client = connected(handle)
    with pytest.raises(APIConnectionError) as exc:
        await resolved(client.find_rows(["subject"]))
    assert exc.value.code == "BAD_RESPONSE"
    assert len(requests) == 1


@pytest.mark.parametrize("change", [
    {"base_url": "https://user:pass@example.com"}, {"base_url": "file:///tmp"}, {"dataset_id": ".."},
    {"base_url": "https://example.com/?token=bad"}, {"token": ""}, {"columns": []},
])
def test_invalid_dataset_connection(change):
    with pytest.raises(ConfigError):
        DatasetClient(**{**OPTIONS, **change})
