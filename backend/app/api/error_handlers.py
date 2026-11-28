"""The one central exception handler set: every error leaves the API as the error envelope."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from ..core.errors import AppError
from ..core.logging import get_logger
from ..schemas.envelope import fail
from .dataset_share_http import share_response_headers

log = get_logger("api")
HTTP_CODES = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 413: "PAYLOAD_TOO_LARGE"}


def respond(err: AppError) -> JSONResponse:
    return JSONResponse(status_code=err.status, content=fail(err.to_dict()), headers=err.headers)


def _field(e) -> str:
    return ".".join(str(x) for x in e.get("loc", []) if x != "body") or "body"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        return respond(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        details = [{"field": _field(e), "message": e.get("msg")} for e in exc.errors()][:10]
        return respond(AppError("VALIDATION_ERROR", details=details))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        err = AppError(HTTP_CODES.get(exc.status_code, "BAD_REQUEST"))
        err.status = exc.status_code
        return respond(err)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("unhandled error: %s", exc)
        return respond(AppError("INTERNAL_ERROR", headers=share_response_headers(request.url.path)))
