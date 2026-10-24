"""Live test against a running backend. scripts/sdk_integration.sh (repository root) starts one and sets the variables."""
import os

import pytest

from superstep import AsyncClient, AuthenticationError, Client, NotFoundError

IT = {k: os.environ.get(f"SUPERSTEP_IT_{k.upper()}") for k in ("base_url", "token", "workflow_id")}
pytestmark = pytest.mark.skipif(not all(IT.values()), reason="set SUPERSTEP_IT_BASE_URL, SUPERSTEP_IT_TOKEN, SUPERSTEP_IT_WORKFLOW_ID")
INPUT = {"message": "where is my order A100"}


def test_live_sync_client():
    with Client(**IT) as c:
        started = c.run(INPUT)
        assert started.status == "queued" and started.poll_url.endswith(started.run_id)
        run = c.wait(started.run_id, timeout=60, poll_interval=0.2)
        assert run.status == "ok" and run.final_state["intent"] == "order_status" and run.source == "api"
        assert c.run_and_wait(INPUT, timeout=60, poll_interval=0.2).status == "ok"
        assert c.run(INPUT, mode="sync").status == "ok"
        with pytest.raises(NotFoundError): c.get_run("does-not-exist")
    with pytest.raises(AuthenticationError), Client(**{**IT, "token": "wft_wrong"}) as bad:
        bad.run(INPUT)


async def test_live_async_client():
    async with AsyncClient(**IT) as c:
        run = await c.run_and_wait(INPUT, timeout=60, poll_interval=0.2)
    assert run.status == "ok" and run.metrics is not None
