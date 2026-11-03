"""The one response envelope for every REST endpoint (DEC-0010).

success: {"success": true,  "data": <payload>, "error": null}
error:   {"success": false, "data": null, "error": {"code", "message", "details"?}}
"""
from typing import Any, Generic, Optional, TypeVar
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


def ok(data: Any) -> dict:
    return {"success": True, "data": data, "error": None}


def fail(error: dict) -> dict:
    return {"success": False, "data": None, "error": error}


class EnvelopeResponse(JSONResponse):
    """Default response class: wraps whatever a route returns in the success envelope."""
    def render(self, content: Any) -> bytes:
        return super().render(content if isinstance(content, dict) and "success" in content and "error" in content else ok(content))


# ---- OpenAPI models of the envelope (documentation and the public spec; the runtime wrapping stays above) ----

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str = Field(..., description="Stable UPPER_SNAKE error code; the contract (see docs/api-errors.md).", examples=["TRIGGER_TOKEN_INVALID"])
    message: str = Field(..., description="English message for humans and logs.", examples=["Missing, invalid or revoked workflow token"])
    details: Optional[Any] = Field(None, description="Optional extra data, e.g. a list of {field, message} for VALIDATION_ERROR.")


class ErrorEnvelope(BaseModel):
    success: bool = Field(False, examples=[False])
    data: None = None
    error: ErrorBody


class Envelope(BaseModel, Generic[T]):
    success: bool = Field(True, examples=[True])
    data: T
    error: None = None


EXAMPLE_PARAMS = {"max_kb": 256, "retry_after": 12, "seconds": 30, "allowed": "document, image", "max_mb": 10, "max": 5,
                  "field": "value"}  # fills message templates in OpenAPI examples


def error_responses(*codes: str) -> dict:
    """OpenAPI `responses` for the given catalog codes, grouped by HTTP status, each with an example."""
    from ..core.errors import CATALOG
    out: dict = {}
    for code in codes:
        status, message = CATALOG[code]
        r = out.setdefault(status, {"model": ErrorEnvelope, "description": "", "content": {"application/json": {"examples": {}}}})
        r["description"] = ", ".join(filter(None, [r["description"], code]))
        r["content"]["application/json"]["examples"][code] = {"value": fail({"code": code, "message": message.format_map(EXAMPLE_PARAMS), "details": None})}
    return out
