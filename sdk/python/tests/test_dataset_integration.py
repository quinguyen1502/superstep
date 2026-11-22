"""Live tests of the sync and async SDK against a disposable Superstep server."""
import inspect
import json
import os
from pathlib import Path

import httpx
import pytest

from superstep import AsyncDatasetClient, AuthenticationError, DatasetClient, PermissionDeniedError, SuperstepError

BASE = os.environ.get("SUPERSTEP_IT_BASE_URL")
FILE = os.environ.get("SUPERSTEP_IT_CHAT_CONFIG")
CONFIG = json.loads(Path(FILE).read_text()) if FILE else None
pytestmark = pytest.mark.skipif(not BASE or not CONFIG, reason="run scripts/sdk_integration.sh for a disposable server")
COLUMNS = [
    {"key": "ticket", "kind": "text", "unique": True, "required": True},
    {"key": "score", "kind": "number"},
]


async def resolved(value):
    return await value if inspect.isawaitable(value) else value


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
async def test_connected_dataset_operations_and_scopes(asynchronous):
    def api(method, path, body=None):
        response = httpx.request(method, BASE + path, json=body, headers={"Authorization": f"Bearer {CONFIG['owner']}"})
        response.raise_for_status()
        return response.json()["data"]

    dataset = api("POST", "/api/datasets", {
        "name": f"SDK Python {asynchronous}", "columns": [{**column, "label": column["key"].title()} for column in COLUMNS],
    })
    base = f"/api/datasets/{dataset['id']}"
    issued = api("POST", f"{base}/access/tokens", {"name": "All", "permission": "read_write", "allow_delete": True})
    writer = api("POST", f"{base}/access/tokens", {"name": "Write", "permission": "write"})
    bodies = []

    def lose_first_response(response):
        if response.request.url.path == base + "/connected":
            bodies.append(response.request.content)
            if len(bodies) == 1:
                assert response.status_code == 200
                raise httpx.ReadError("simulated loss after the server committed")

    async def lose_first_async(response):
        lose_first_response(response)

    transport = (httpx.AsyncClient(event_hooks={"response": [lose_first_async]}) if asynchronous
                 else httpx.Client(event_hooks={"response": [lose_first_response]}))
    kind = AsyncDatasetClient if asynchronous else DatasetClient
    client = kind(base_url=BASE, dataset_id=dataset["id"], token=issued["token"], columns=COLUMNS, http_client=transport)
    write = kind(base_url=BASE, dataset_id=dataset["id"], token=writer["token"], columns=COLUMNS)
    drift = kind(base_url=BASE, dataset_id=dataset["id"], token=issued["token"], columns=[
        COLUMNS[0], {**COLUMNS[1], "kind": "text"},
    ])
    fields = ["ticket", "score"]
    try:
        inserted = await resolved(client.insert_row({"ticket": "T1", "score": 2}, fields=fields))
        row_id = inserted["row"]["id"]
        assert bodies[0] == bodies[1]
        assert inserted["inserted"] and inserted["row"]["values"] == {"ticket": "T1", "score": 2}
        assert (await resolved(client.get_row(row_id, ["score"])))["values"] == {"score": 2}

        found = await resolved(client.find_rows(fields, {"filter_tree": {
            "type": "group", "conjunction": "and", "children": [
                {"type": "rule", "field": "score", "op": "gte", "value": 2},
            ],
        }, "sorts": [{"field": "score"}], "limit": 1}))
        assert [row["id"] for row in found["items"]] == [row_id] and found["next_offset"] is None
        updated = await resolved(client.upsert_row("ticket", {"ticket": "T1", "score": 3}, fields=fields,
                                                   operation_id="example:T1"))
        assert not updated["inserted"] and updated["row"]["id"] == row_id
        assert (await resolved(client.aggregate_rows(fields, {"summaries": {"score": "sum"}})))["groups"] == [
            {"group": None, "total": 1, "values": {"score": 3}},
        ]
        with pytest.raises(SuperstepError) as mismatch:
            await resolved(drift.find_rows(fields))
        assert mismatch.value.code == "DATASET_BINDING_SCHEMA_MISMATCH"

        identity = await resolved(write.insert_row({"ticket": "T2", "score": 4}))
        assert set(identity["row"]) == {"id", "revision"}
        with pytest.raises(PermissionDeniedError) as projection:
            await resolved(write.upsert_row("ticket", {"ticket": "T2"}, fields=["score"]))
        assert projection.value.code == "DATASET_GRANT_DENIED"
        with pytest.raises(PermissionDeniedError) as delete:
            await resolved(write.delete_row({"row_id": row_id}, fields))
        assert delete.value.code == "DATASET_TOKEN_SCOPE"
        assert await resolved(client.delete_row({"key": "ticket", "value": "T1"}, fields)) == {
            "row_id": row_id, "deleted": True,
        }
        api("DELETE", f"{base}/access/tokens/{issued['id']}")
        with pytest.raises(AuthenticationError) as revoked:
            await resolved(client.find_rows(fields))
        assert revoked.value.code == "AUTH_TOKEN_INVALID"
    finally:
        for resource in (client, write, drift, transport):
            await resolved(resource.aclose() if asynchronous else resource.close())
