import httpx
import pytest

from superstep import (APIConnectionError, AuthenticationError, Client, ConfigError, InvalidRequestError, NotFoundError,
                       PayloadTooLargeError, RateLimitError, Run, ServerError, SuperstepError, WaitTimeoutError)
from superstep._base import poll_delays
from conftest import BASE, TOKEN, WID, Recorder, env, err

QUEUED = {"run_id": "r1", "status": "queued", "poll_url": f"{BASE}/api/hooks/workflows/{WID}/runs/r1"}
DONE = {"run_id": "r1", "workflow_id": WID, "status": "ok", "source": "api", "final_state": {"answer": 42}, "error": None, "waiting": None,
        "metrics": {"duration_ms": 12.5, "tokens_in": 1, "tokens_out": 2, "cost_usd": 0.0, "error_count": 0}, "trace_url": None,
        "started": 1.0, "ended": 2.0}
RUNNING = {**DONE, "status": "running", "final_state": None, "metrics": None, "ended": None}


def make(rec, **kw):
    return Client(WID, TOKEN, BASE + "/", http_client=httpx.Client(transport=httpx.MockTransport(rec)), **kw)


def test_run_sends_token_body_and_parses(no_env):
    rec = Recorder(env(QUEUED, 202))
    run = make(rec).run({"q": 1}, callback_url="https://hook.example.com")
    req = rec.requests[0]
    assert req.method == "POST" and str(req.url) == f"{BASE}/api/hooks/workflows/{WID}/runs"
    assert req.headers["x-workflow-token"] == TOKEN and req.headers["user-agent"].startswith("superstep-python/")
    assert rec.body() == {"input": {"q": 1}, "mode": "async", "callback_url": "https://hook.example.com"}
    assert isinstance(run, Run) and run.status == "queued" and not run.done and run.poll_url == QUEUED["poll_url"]


def test_get_run_typed_model(no_env):
    rec = Recorder(env(DONE))
    run = make(rec).get_run("r 1")
    assert str(rec.requests[0].url).endswith("/runs/r%201")
    assert run.done and run.final_state == {"answer": 42} and run.metrics.duration_ms == 12.5 and run.raw["source"] == "api"


def test_run_and_wait_polls_with_backoff(no_env, no_sleep):
    rec = Recorder(env(QUEUED, 202), env(RUNNING), env(RUNNING), env(RUNNING), env(DONE))
    run = make(rec).run_and_wait({}, poll_interval=1, backoff=2, max_poll_interval=3)
    assert run.status == "ok" and no_sleep == [1, 2, 3] and len(rec.requests) == 5


def test_run_and_wait_times_out(no_env, monkeypatch):
    clock = iter(range(0, 1000, 5))
    monkeypatch.setattr("superstep._client.time.monotonic", lambda: next(clock))
    monkeypatch.setattr("superstep._client.time.sleep", lambda s: None)
    rec = Recorder(env(QUEUED, 202), *[env(RUNNING)] * 10)
    with pytest.raises(WaitTimeoutError) as e:
        make(rec).run_and_wait({}, timeout=12)
    assert e.value.run.status == "running" and e.value.code == "WAIT_TIMEOUT"


def test_sync_mode_returns_the_result(no_env):
    rec = Recorder(env(DONE))
    assert make(rec).run({}, mode="sync").status == "ok" and rec.body()["mode"] == "sync"
    with pytest.raises(ValueError): make(Recorder()).run({}, mode="later")


@pytest.mark.parametrize("code,status,cls", [
    ("TRIGGER_TOKEN_INVALID", 401, AuthenticationError), ("RUN_NOT_FOUND", 404, NotFoundError), ("RUN_INPUT_INVALID", 400, InvalidRequestError),
    ("CALLBACK_URL_INVALID", 400, InvalidRequestError), ("VALIDATION_ERROR", 422, InvalidRequestError),
    ("RUN_INPUT_TOO_LARGE", 413, PayloadTooLargeError), ("INTERNAL_ERROR", 500, ServerError), ("SOMETHING_NEW", 503, ServerError),
    ("SOMETHING_NEW", 418, SuperstepError)])
def test_errors_are_typed_by_code(no_env, code, status, cls):
    with pytest.raises(cls) as e:
        make(Recorder(err(code, status, details=[{"field": "mode"}]))).get_run("r1")
    assert type(e.value) is cls and e.value.code == code and e.value.status == status


def test_rate_limit_exposes_retry_after(no_env):
    with pytest.raises(RateLimitError) as e:
        make(Recorder(err("RATE_LIMITED", 429, headers={"Retry-After": "7"}))).run({})
    assert e.value.retry_after == 7.0


def test_non_envelope_and_network_errors(no_env):
    with pytest.raises(APIConnectionError) as e:
        make(Recorder(httpx.Response(502, text="<html>bad gateway</html>"))).get_run("r1")
    assert e.value.code == "BAD_RESPONSE"

    def down(request): raise httpx.ConnectError("refused", request=request)
    with pytest.raises(APIConnectionError) as e:
        make(Recorder(down)).get_run("r1")
    assert e.value.code == "CONNECTION_ERROR"


def test_env_var_fallback(no_env, monkeypatch):
    with pytest.raises(ConfigError) as e: Client()
    assert "SUPERSTEP_TOKEN" in str(e.value)
    monkeypatch.setenv("SUPERSTEP_BASE_URL", "http://env.test/"); monkeypatch.setenv("SUPERSTEP_TOKEN", "wft_env")
    monkeypatch.setenv("SUPERSTEP_WORKFLOW_ID", "wenv")
    with Client() as c:
        assert c.config.runs_url("x") == "http://env.test/api/hooks/workflows/wenv/runs/x" and c.config.token == "wft_env"
    assert Client(token="wft_arg").config.token == "wft_arg"  # arguments win


def test_poll_delays():
    d = poll_delays(0.5, 2, 2)
    assert [next(d) for _ in range(5)] == [0.5, 1, 2, 2, 2]
    with pytest.raises(ValueError): next(poll_delays(0, 1, 1))


SCHEDULE = {"id": "s1", "name": "Morning", "cron": "0 9 * * MON-FRI", "timezone": "Asia/Ho_Chi_Minh", "input": {"message": "hi"},
            "enabled": True, "next_runs": [1.0], "last_run": None, "last_run_id": None, "note": None, "created": 1.0}


def test_schedules_call_the_public_paths(no_env):
    rec = Recorder(env(SCHEDULE, 201), env([SCHEDULE]), env({**SCHEDULE, "enabled": False}), env({"ok": True}), env({"next_runs": [9.0, 10.0]}))
    client = make(rec)
    created = client.create_schedule("0 9 * * MON-FRI", name="Morning", timezone="Asia/Ho_Chi_Minh", input={"message": "hi"})
    assert created["id"] == "s1" and rec.requests[0].method == "POST" and str(rec.requests[0].url).endswith("/schedules")
    assert rec.body() == {"name": "Morning", "cron": "0 9 * * MON-FRI", "timezone": "Asia/Ho_Chi_Minh", "input": {"message": "hi"}, "enabled": True}
    assert client.list_schedules()[0]["id"] == "s1" and rec.requests[1].method == "GET"
    assert client.update_schedule("s 1", enabled=False)["enabled"] is False
    assert rec.requests[2].method == "PATCH" and str(rec.requests[2].url).endswith("/schedules/s%201") and rec.body(2) == {"enabled": False}
    assert client.delete_schedule("s1") == {"ok": True} and rec.requests[3].method == "DELETE"
    assert client.preview_schedule("@daily") == [9.0, 10.0]
    assert rec.requests[4].method == "POST" and str(rec.requests[4].url).endswith("/schedules/preview") and rec.body(4) == {"cron": "@daily", "timezone": "UTC"}
    with pytest.raises(TypeError): client.update_schedule("s1", colour="red")


@pytest.mark.parametrize("code,call", [
    ("SCHEDULE_CRON_INVALID", lambda c: c.create_schedule("nope")),
    ("SCHEDULE_LIMIT", lambda c: c.create_schedule("@daily")),
    ("SCHEDULE_NOT_FOUND", lambda c: c.delete_schedule("missing"))])
def test_schedule_errors_are_typed(no_env, code, call):
    status = 404 if code == "SCHEDULE_NOT_FOUND" else 400
    cls = NotFoundError if status == 404 else InvalidRequestError
    with pytest.raises(cls) as e:
        call(make(Recorder(err(code, status))))
    assert e.value.code == code
