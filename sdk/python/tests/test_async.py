import httpx
import pytest

from superstep import AsyncClient, AuthenticationError, WaitTimeoutError
from conftest import BASE, TOKEN, WID, Recorder, env, err
from test_client import DONE, QUEUED, RUNNING


@pytest.fixture
def no_async_sleep(monkeypatch):
    slept = []

    async def fake(s): slept.append(s)
    monkeypatch.setattr("superstep._client.asyncio.sleep", fake)
    return slept


def make(rec):
    return AsyncClient(WID, TOKEN, BASE, http_client=httpx.AsyncClient(transport=httpx.MockTransport(rec)))


async def test_async_run_and_wait(no_env, no_async_sleep):
    rec = Recorder(env(QUEUED, 202), env(RUNNING), env(DONE))
    async with make(rec) as c:
        run = await c.run_and_wait({"x": 1}, poll_interval=0.5)
    assert run.final_state == {"answer": 42} and no_async_sleep == [0.5] and rec.body() == {"input": {"x": 1}, "mode": "async"}


async def test_async_errors_and_timeout(no_env, no_async_sleep):
    with pytest.raises(AuthenticationError):
        await make(Recorder(err("TRIGGER_TOKEN_INVALID", 401))).get_run("r1")
    with pytest.raises(WaitTimeoutError):
        await make(Recorder(env(QUEUED, 202), env(RUNNING))).run_and_wait({}, timeout=0)


async def test_async_schedules(no_env):
    rec = Recorder(env({"id": "s1", "enabled": True}, 201), env({"next_runs": [9.0]}))
    async with make(rec) as client:
        created = await client.create_schedule("@daily", name="Nightly")
        times = await client.preview_schedule("0 9 * * MON-FRI", timezone="Asia/Ho_Chi_Minh")
    assert created["id"] == "s1" and times == [9.0]
    assert rec.body() == {"name": "Nightly", "cron": "@daily", "timezone": "UTC", "input": {}, "enabled": True}
    assert str(rec.requests[1].url).endswith("/schedules/preview")
