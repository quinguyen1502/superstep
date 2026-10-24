"""Sync and async clients. Both send the same requests (`_base`); only the transport and sleeping differ."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

import httpx

from ._base import DEFAULT_TIMEOUT, Config, parse, poll_delays, start_body
from ._errors import APIConnectionError, WaitTimeoutError
from ._models import Run


def _json(r: httpx.Response) -> Any:
    try: return r.json()
    except ValueError: return None


class _Common:
    def __init__(self, workflow_id: Optional[str], token: Optional[str], base_url: Optional[str]):
        self.config = Config.resolve(base_url, token, workflow_id)

    def _deadline(self, timeout: Optional[float]) -> Optional[float]:
        return None if timeout is None else time.monotonic() + timeout

    @staticmethod
    def _sleep_for(delay: float, deadline: Optional[float], run: Run) -> float:
        if deadline is None: return delay
        left = deadline - time.monotonic()
        if left <= 0: raise WaitTimeoutError(f"Run {run.run_id} still {run.status} after the timeout", run)
        return min(delay, left)


class Client(_Common):
    """Synchronous client.

        client = Client(workflow_id="example", token="wft_...", base_url="http://localhost:8080")
        run = client.run_and_wait({"message": "hi"}, timeout=60)

    Unset arguments fall back to SUPERSTEP_WORKFLOW_ID, SUPERSTEP_TOKEN and SUPERSTEP_BASE_URL.
    """

    def __init__(self, workflow_id: Optional[str] = None, token: Optional[str] = None, base_url: Optional[str] = None, *,
                 timeout: float = DEFAULT_TIMEOUT, http_client: Optional[httpx.Client] = None):
        super().__init__(workflow_id, token, base_url)
        self._http = http_client or httpx.Client(timeout=timeout)
        self._owns_http = http_client is None

    def _send(self, method: str, url: str, body: Optional[Dict[str, Any]] = None) -> Run:
        try: r = self._http.request(method, url, json=body, headers=self.config.headers)
        except httpx.HTTPError as e: raise APIConnectionError(str(e) or type(e).__name__, code="CONNECTION_ERROR") from e
        return parse(r.status_code, dict(r.headers), _json(r))

    def run(self, input: Optional[Dict[str, Any]] = None, *, mode: str = "async", callback_url: Optional[str] = None) -> Run:
        """Start a run. `async` returns at once (status `queued`); `sync` waits up to the server's limit."""
        return self._send("POST", self.config.runs_url(), start_body(input, mode, callback_url))

    def get_run(self, run_id: str) -> Run:
        return self._send("GET", self.config.runs_url(run_id))

    def wait(self, run_id: str, *, timeout: Optional[float] = 300.0, poll_interval: float = 1.0, max_poll_interval: float = 10.0,
             backoff: float = 1.5) -> Run:
        """Poll until the run is done. Raises WaitTimeoutError after `timeout` seconds (None waits forever)."""
        deadline, delays = self._deadline(timeout), poll_delays(poll_interval, max_poll_interval, backoff)
        while True:
            run = self.get_run(run_id)
            if run.done: return run
            time.sleep(self._sleep_for(next(delays), deadline, run))

    def run_and_wait(self, input: Optional[Dict[str, Any]] = None, *, timeout: Optional[float] = 300.0, poll_interval: float = 1.0,
                     max_poll_interval: float = 10.0, backoff: float = 1.5, callback_url: Optional[str] = None) -> Run:
        """Start a run and poll (interval growing by `backoff` up to `max_poll_interval`) until it is done."""
        started = self.run(input, callback_url=callback_url)
        if started.done: return started
        return self.wait(started.run_id, timeout=timeout, poll_interval=poll_interval, max_poll_interval=max_poll_interval, backoff=backoff)

    def close(self) -> None:
        if self._owns_http: self._http.close()

    def __enter__(self) -> "Client": return self

    def __exit__(self, *exc: Any) -> None: self.close()


class AsyncClient(_Common):
    """Asynchronous client with the same methods as `Client`, as coroutines."""

    def __init__(self, workflow_id: Optional[str] = None, token: Optional[str] = None, base_url: Optional[str] = None, *,
                 timeout: float = DEFAULT_TIMEOUT, http_client: Optional[httpx.AsyncClient] = None):
        super().__init__(workflow_id, token, base_url)
        self._http = http_client or httpx.AsyncClient(timeout=timeout)
        self._owns_http = http_client is None

    async def _send(self, method: str, url: str, body: Optional[Dict[str, Any]] = None) -> Run:
        try: r = await self._http.request(method, url, json=body, headers=self.config.headers)
        except httpx.HTTPError as e: raise APIConnectionError(str(e) or type(e).__name__, code="CONNECTION_ERROR") from e
        return parse(r.status_code, dict(r.headers), _json(r))

    async def run(self, input: Optional[Dict[str, Any]] = None, *, mode: str = "async", callback_url: Optional[str] = None) -> Run:
        return await self._send("POST", self.config.runs_url(), start_body(input, mode, callback_url))

    async def get_run(self, run_id: str) -> Run:
        return await self._send("GET", self.config.runs_url(run_id))

    async def wait(self, run_id: str, *, timeout: Optional[float] = 300.0, poll_interval: float = 1.0, max_poll_interval: float = 10.0,
                   backoff: float = 1.5) -> Run:
        deadline, delays = self._deadline(timeout), poll_delays(poll_interval, max_poll_interval, backoff)
        while True:
            run = await self.get_run(run_id)
            if run.done: return run
            await asyncio.sleep(self._sleep_for(next(delays), deadline, run))

    async def run_and_wait(self, input: Optional[Dict[str, Any]] = None, *, timeout: Optional[float] = 300.0, poll_interval: float = 1.0,
                           max_poll_interval: float = 10.0, backoff: float = 1.5, callback_url: Optional[str] = None) -> Run:
        started = await self.run(input, callback_url=callback_url)
        if started.done: return started
        return await self.wait(started.run_id, timeout=timeout, poll_interval=poll_interval, max_poll_interval=max_poll_interval, backoff=backoff)

    async def aclose(self) -> None:
        if self._owns_http: await self._http.aclose()

    async def __aenter__(self) -> "AsyncClient": return self

    async def __aexit__(self, *exc: Any) -> None: await self.aclose()
