import json
from typing import Callable, List

import httpx
import pytest

BASE, WID, TOKEN = "http://superstep.test", "wf1", "wft_test"


def env(data, status=200, headers=None):
    return httpx.Response(status, json={"success": True, "data": data, "error": None}, headers=headers)


def err(code, status, message="boom", details=None, headers=None):
    return httpx.Response(status, json={"success": False, "data": None, "error": {"code": code, "message": message, "details": details}},
                          headers=headers)


class Recorder:
    """A scripted server: each request pops the next response (or calls it with the request)."""

    def __init__(self, *responses):
        self.responses: List = list(responses)
        self.requests: List[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        nxt = self.responses.pop(0)
        return nxt(request) if isinstance(nxt, Callable) else nxt

    def body(self, i=0):
        return json.loads(self.requests[i].content)


@pytest.fixture
def no_env(monkeypatch):
    for k in ("SUPERSTEP_BASE_URL", "SUPERSTEP_TOKEN", "SUPERSTEP_WORKFLOW_ID"): monkeypatch.delenv(k, raising=False)


@pytest.fixture
def no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr("superstep._client.time.sleep", slept.append)
    return slept
