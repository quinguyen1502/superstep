"""App factory. `app.main:app` stays the uvicorn entrypoint."""
import asyncio, logging
from .api.body_limit import BodyLimit
from .api.chat_cors import ChatCors
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Route
from .api.deps import get_db, get_job_queue, get_probes, get_telemetry, usage_service, public_chat_service, run_service, run_worker
from .api import deps
from .api.http_metrics import HttpMetrics
from .api.http_spans import HttpSpans
from .api.request_context import RequestContext
from .core.logging import configure as configure_logging, get_logger, redact_tokens
from .core import config, crypto
from .api.error_handlers import register_error_handlers
from .api.routes import ROUTERS
from .api.static import mount_frontend
from .api.openapi_public import install_public_docs
from .api.asyncapi_public import install_asyncapi
from .api.demo import install_demo_guard
from .api.mcp_server import PATH as MCP_PATH, McpApp
from .core.security import check_secret
from .engine import code_runtime
from .schemas.envelope import EnvelopeResponse
from .services.seed import bootstrap


SWEEP_EVERY = 60  # seconds


async def expire_waiting_loop() -> None:
    while True:
        try: await asyncio.to_thread(run_service().expire_waiting)
        except asyncio.CancelledError: raise
        except Exception: get_logger("sweeper").exception("expiring waiting runs failed")
        try:
            from .api.deps import browser_artifact_service, browser_session_service
            await asyncio.to_thread(browser_artifact_service().sweep)
            await asyncio.to_thread(browser_session_service().sweep)
        except asyncio.CancelledError: raise
        except Exception: get_logger("sweeper").exception("expiring browser artifacts failed")
        await asyncio.sleep(SWEEP_EVERY)


def create_app() -> FastAPI:
    configure_logging(config.log_format(), config.log_level())  # STUDIO_LOG_FORMAT / STUDIO_LOG_LEVEL
    check_secret(); crypto.check_key()
    config.studio_timezone()
    code_runtime.warn_if_unisolated()  # once at start-up
    get_telemetry().instrument(get_db().engine)  # SQL and Redis spans (no-op unless STUDIO_OTEL_INSTRUMENT is on)
    bootstrap(get_db(), jobs=get_job_queue())  # alembic upgrade head + demo user + example workflow
    try:  # rows from 0.10.1 learn the folder or bucket/prefix they were written to
        from .api.deps import attachment_files
        attachment_files().backfill_locations()
    except Exception as e: logging.getLogger(__name__).warning("attachment locations not recorded (%s)", type(e).__name__)
    mcp_app = McpApp()  # MCP server for workflow tokens
    @asynccontextmanager
    async def lifespan(_app):
        w = run_worker() if config.worker_enabled() else None  # executes queued API runs
        if w:
            w.start(config.worker_concurrency())
            await w.recover_unfinished()  # in-memory queue: runs that were going when the server stopped
        get_telemetry().watch(get_probes(), w, product=lambda: usage_service().gauges(), pool=get_db().pool_status)  # metric gauges (no-op unless STUDIO_OTEL_METRICS is on)
        sweeper = asyncio.create_task(expire_waiting_loop())  # waiting runs past STUDIO_WAIT_TTL -> expired
        async with mcp_app.running(): yield
        sweeper.cancel()
        if w: await w.stop()

    app = FastAPI(title="Superstep", default_response_class=EnvelopeResponse, lifespan=lifespan)  # every REST response is an envelope
    if origins := config.cors_origins():  # STUDIO_CORS_ORIGINS; production default: same-origin only
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])
    redact_tokens("uvicorn.access", "uvicorn.error")  # WebSocket URLs carry ?token=<JWT>
    register_error_handlers(app)
    app.add_middleware(BodyLimit)  # request body ceilings without a proxy too
    app.add_middleware(ChatCors, public=public_chat_service)
    if config.demo_mode(): install_demo_guard(app)  # STUDIO_DEMO_MODE: the shared visitor account is read-only
    app.add_middleware(HttpMetrics, telemetry=lambda: deps.get_telemetry())  # every response, by route template
    app.add_middleware(HttpSpans, telemetry=lambda: deps.get_telemetry())  # opt-in server spans (STUDIO_OTEL_INSTRUMENT)
    app.add_middleware(RequestContext)  # outermost: X-Request-ID for every log line of the request
    for r in ROUTERS: app.include_router(r)
    app.router.routes.append(Route(MCP_PATH, endpoint=mcp_app))  # Streamable HTTP, all methods
    install_asyncapi(app)  # GET /asyncapi.public.yaml: the chat socket protocol v1
    install_public_docs(app)  # GET /openapi.public.json + /docs/public: the workflow-trigger API only
    # all-in-one image: the built UI on the same origin, after the API routes; frame headers
    mount_frontend(app, config.static_dir(), lambda slug: public_chat_service().frame_ancestors(slug))
    return app


app = create_app()
