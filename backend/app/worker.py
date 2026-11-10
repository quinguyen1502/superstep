"""Dedicated run worker process: `python -m app.worker` (needs REDIS_URL so jobs are shared with the API)."""
import asyncio
from .api.deps import get_db, get_job_queue, get_probes, get_telemetry, usage_service, run_service, run_worker
from .core import config
from .core.logging import configure as configure_logging, get_logger
from .services.seed import bootstrap
from .engine import code_runtime


async def main() -> None:
    configure_logging(config.log_format(), config.log_level())  # STUDIO_LOG_FORMAT / STUDIO_LOG_LEVEL
    get_telemetry().instrument(get_db().engine)  # SQL and Redis spans (no-op unless STUDIO_OTEL_INSTRUMENT is on)
    bootstrap(get_db(), jobs=get_job_queue()); code_runtime.warn_if_unisolated()
    w = run_worker(); w.start(config.worker_concurrency())
    get_telemetry().watch(get_probes(), w, product=lambda: usage_service().gauges())  # metric gauges (no-op unless STUDIO_OTEL_METRICS is on)
    get_logger("worker").info("worker started (%s queue, concurrency %s)", w.jobs.kind, config.worker_concurrency())
    await asyncio.gather(*w._tasks)


if __name__ == "__main__":
    asyncio.run(main())
