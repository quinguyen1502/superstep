"""Typed errors, mapped from the API's stable error codes (docs/api-errors.md), then from the HTTP status."""
from __future__ import annotations

from typing import Any, Dict, Optional, Type


class SuperstepError(Exception):
    """Base class. `code` is the API error code (or a client-side one such as CONNECTION_ERROR)."""

    def __init__(self, message: str, *, code: str = "UNKNOWN", status: Optional[int] = None, details: Any = None,
                 headers: Optional[Dict[str, str]] = None):
        super().__init__(message)
        self.message, self.code, self.status, self.details, self.headers = message, code, status, details, headers or {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, status={self.status!r}, message={self.message!r})"


class ConfigError(SuperstepError):
    """Missing base URL, token or workflow id."""


class APIConnectionError(SuperstepError):
    """The request did not reach the server or the response was not the API's envelope."""


class AuthenticationError(SuperstepError):
    """401 TRIGGER_TOKEN_INVALID: missing, invalid or revoked token, or a token of another workflow."""


class NotFoundError(SuperstepError):
    """404, e.g. RUN_NOT_FOUND."""


class InvalidRequestError(SuperstepError):
    """400 / 422: RUN_INPUT_INVALID, CALLBACK_URL_INVALID, VALIDATION_ERROR (see `details`)."""


class PayloadTooLargeError(SuperstepError):
    """413 RUN_INPUT_TOO_LARGE."""


class RateLimitError(SuperstepError):
    """429 RATE_LIMITED. `retry_after` is the number of seconds to wait."""

    @property
    def retry_after(self) -> Optional[float]:
        value = self.headers.get("retry-after") or self.headers.get("Retry-After")
        try: return float(value) if value is not None else None
        except ValueError: return None


class ServerError(SuperstepError):
    """5xx, e.g. INTERNAL_ERROR."""


class WaitTimeoutError(SuperstepError):
    """`run_and_wait` gave up before the run finished. `run` is the last state seen."""

    def __init__(self, message: str, run: Any):
        super().__init__(message, code="WAIT_TIMEOUT")
        self.run = run


BY_CODE: Dict[str, Type[SuperstepError]] = {
    "TRIGGER_TOKEN_INVALID": AuthenticationError,
    "RUN_NOT_FOUND": NotFoundError,
    "WORKFLOW_NOT_FOUND": NotFoundError,
    "NOT_FOUND": NotFoundError,
    "RUN_INPUT_INVALID": InvalidRequestError,
    "CALLBACK_URL_INVALID": InvalidRequestError,
    "VALIDATION_ERROR": InvalidRequestError,
    "BAD_REQUEST": InvalidRequestError,
    "RUN_INPUT_TOO_LARGE": PayloadTooLargeError,
    "PAYLOAD_TOO_LARGE": PayloadTooLargeError,
    "RATE_LIMITED": RateLimitError,
    "INTERNAL_ERROR": ServerError,
}
BY_STATUS: Dict[int, Type[SuperstepError]] = {401: AuthenticationError, 404: NotFoundError, 400: InvalidRequestError,
                                              422: InvalidRequestError, 413: PayloadTooLargeError, 429: RateLimitError}


def error_for(status: int, code: str, message: str, details: Any = None, headers: Optional[Dict[str, str]] = None) -> SuperstepError:
    cls = BY_CODE.get(code) or BY_STATUS.get(status) or (ServerError if status >= 500 else SuperstepError)
    return cls(message, code=code, status=status, details=details, headers=headers)
