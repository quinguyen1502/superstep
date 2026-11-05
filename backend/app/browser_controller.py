"""Dedicated operator-deployed browser control API. Never mount this on the public Studio API.

TLS is required at the authenticated control plane (reverse proxy or uvicorn TLS).
No browser/page shares the listener's network namespace. Default bind is localhost.
"""
from contextlib import asynccontextmanager
import hmac
import json
import os

from fastapi import Depends, FastAPI, Request
from pydantic import ValidationError

from .api.error_handlers import register_error_handlers
from .core.errors import AppError
from .engine.browser_contract import WorkerCommand, WorkerArtifact, WorkerControl
from .engine.browser_remote import RemoteOpen
from .schemas.envelope import EnvelopeResponse
from .services.browser_controller_service import BrowserControllerService


def create_app(controller=None, token=None):
    token = token or os.environ.get('STUDIO_BROWSER_CONTROL_TOKEN', '')
    if len(token) < 32: raise ValueError('Browser controller requires a token of at least 32 characters')
    if controller is None:
        from .engine.browser_worker import LocalBrowserWorker
        from .engine.browser_cleanup import reap_controller
        from .engine.sandbox.container import docker_exe
        from functools import partial
        identity = os.environ.get('STUDIO_BROWSER_CONTROL_ID', '')
        # One process owns this ID. A restart destroys old pages rather than reattaching/replaying.
        reap_controller(docker_exe(), identity)
        controller = BrowserControllerService(partial(LocalBrowserWorker, resource_owner=identity))
    @asynccontextmanager
    async def lifespan(app):
        yield
        controller.close()
    app = FastAPI(default_response_class=EnvelopeResponse, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    register_error_handlers(app)

    def authorised(request: Request):
        if not hmac.compare_digest(request.headers.get('Authorization', '').encode(), ('Bearer ' + token).encode()):
            raise AppError('AUTH_TOKEN_INVALID')

    async def body(request, model):
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 256 * 1024: raise AppError('PAYLOAD_TOO_LARGE')
        try: return model.model_validate(json.loads(raw))
        except (ValueError, TypeError, ValidationError): raise AppError('VALIDATION_ERROR') from None

    @app.get('/v1/info', dependencies=[Depends(authorised)])
    def info(): return controller.info()

    @app.post('/v1/open', dependencies=[Depends(authorised)])
    async def open_session(request: Request):
        value = await body(request, RemoteOpen)
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(controller.open, value)

    # Fixed routes/schemas only; no arbitrary control method forwarded from a request body.
    def register(method, model):
        async def invoke(request: Request):
            value = await body(request, model)
            from starlette.concurrency import run_in_threadpool
            return await run_in_threadpool(controller.invoke, method, value)
        app.add_api_route('/v1/' + method, invoke, methods=['POST'], dependencies=[Depends(authorised)])
    for method, model in [('command', WorkerCommand), ('approve', WorkerCommand), ('artifact', WorkerArtifact), ('close', WorkerControl), ('health', WorkerControl)]:
        register(method, model)
    return app


def main():
    import uvicorn
    uvicorn.run(create_app(), host=os.environ.get('STUDIO_BROWSER_CONTROL_HOST', '127.0.0.1'),
                port=int(os.environ.get('STUDIO_BROWSER_CONTROL_PORT', '8090')), access_log=False)


if __name__ == '__main__': main()
