"""What the sync and async clients share: configuration, request building, envelope parsing and the poll schedule."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional
from urllib.parse import quote

from ._errors import APIConnectionError, ConfigError, error_for
from ._models import Run
from ._version import __version__

ENV_BASE_URL, ENV_TOKEN, ENV_WORKFLOW_ID = "SUPERSTEP_BASE_URL", "SUPERSTEP_TOKEN", "SUPERSTEP_WORKFLOW_ID"
DEFAULT_TIMEOUT = 60.0  # per HTTP request; a `sync` start may hold the connection up to STUDIO_SYNC_WAIT_MAX (30 s)


@dataclass(frozen=True)
class Config:
    base_url: str
    token: str
    workflow_id: str

    @classmethod
    def resolve(cls, base_url: Optional[str], token: Optional[str], workflow_id: Optional[str]) -> "Config":
        values = {"base_url": base_url or os.environ.get(ENV_BASE_URL), "token": token or os.environ.get(ENV_TOKEN),
                  "workflow_id": workflow_id or os.environ.get(ENV_WORKFLOW_ID)}
        env = {"base_url": ENV_BASE_URL, "token": ENV_TOKEN, "workflow_id": ENV_WORKFLOW_ID}
        missing = [f"{k} (or {env[k]})" for k, v in values.items() if not v]
        if not values["base_url"]: raise ConfigError("Missing " + ", ".join(missing), code="CONFIG_MISSING")
        return cls(base_url=str(values["base_url"]).rstrip("/"), token=str(values["token"] or ""), workflow_id=str(values["workflow_id"] or ""))

    @property
    def headers(self) -> Dict[str, str]:
        return {"X-Workflow-Token": self.token, "Accept": "application/json", "User-Agent": f"superstep-python/{__version__}"}

    def runs_url(self, run_id: Optional[str] = None) -> str:
        if not self.token or not self.workflow_id: raise ConfigError("Workflow runs require workflow_id and token", code="CONFIG_MISSING")
        url = f"{self.base_url}/api/hooks/workflows/{quote(self.workflow_id, safe='')}/runs"
        return f"{url}/{quote(run_id, safe='')}" if run_id else url

    def schedules_url(self, schedule_id: Optional[str] = None, *, preview: bool = False) -> str:
        if not self.token or not self.workflow_id: raise ConfigError("Workflow schedules require workflow_id and token", code="CONFIG_MISSING")
        url = f"{self.base_url}/api/hooks/workflows/{quote(self.workflow_id, safe='')}/schedules"
        if preview: return f"{url}/preview"
        return f"{url}/{quote(schedule_id, safe='')}" if schedule_id else url


def start_body(input: Optional[Dict[str, Any]], mode: str, callback_url: Optional[str]) -> Dict[str, Any]:
    if mode not in ("async", "sync"): raise ValueError("mode must be 'async' or 'sync'")
    body: Dict[str, Any] = {"input": input or {}, "mode": mode}
    if callback_url: body["callback_url"] = callback_url
    return body


def schedule_body(cron: str, *, name: str = "Schedule", timezone: str = "UTC", input: Optional[Dict[str, Any]] = None,
                  enabled: bool = True) -> Dict[str, Any]:
    return {"name": name, "cron": cron, "timezone": timezone, "input": input or {}, "enabled": enabled}


def schedule_patch(fields: Dict[str, Any]) -> Dict[str, Any]:
    allowed = ("name", "cron", "timezone", "input", "enabled")
    unknown = [key for key in fields if key not in allowed]
    if unknown: raise TypeError("Unknown schedule field: " + ", ".join(sorted(unknown)))
    return {key: fields[key] for key in allowed if key in fields}


def unwrap(status: int, headers: Dict[str, str], payload: Any) -> Any:
    """Unwrap the envelope; raise the typed error for an error envelope."""
    if not isinstance(payload, dict) or type(payload.get("success")) is not bool or (payload["success"] and (status >= 400 or "data" not in payload)):
        raise APIConnectionError(f"Unexpected response (HTTP {status}); is base_url a Superstep server?", code="BAD_RESPONSE", status=status)
    if not payload["success"]:
        err = payload.get("error") or {}
        raise error_for(status, err.get("code", "UNKNOWN"), err.get("message", f"HTTP {status}"), err.get("details"), headers)
    return payload["data"]


def parse(status: int, headers: Dict[str, str], payload: Any) -> Run:
    return Run.from_dict(unwrap(status, headers, payload))


def poll_delays(initial: float, maximum: float, factor: float) -> Iterator[float]:
    """initial, initial*factor, ... capped at maximum."""
    if initial <= 0 or factor < 1: raise ValueError("poll_interval must be > 0 and backoff >= 1")
    delay = initial
    while True:
        yield min(delay, maximum)
        delay *= factor
