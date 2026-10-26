# Sandbox service for STUDIO_CODE_RUNTIME=remote (app/sandbox_service.py, docs/deploy/sandbox.md). Build context: the
# repository root: docker build -f docker/studio-sandbox/Dockerfile -t superstep-sandbox .
# It contains only the Code runtime of the backend (standard library + httpx), Python packages for user code and
# Deno with the cached TypeScript allowlist. No studio secret belongs in its environment: only STUDIO_SANDBOX_TOKEN.
# The service runs as root so that every call can drop to its own uid (STUDIO_CODE_RUN_AS..+STUDIO_CODE_CONCURRENCY).
ARG DENO_VERSION=2.9.8
FROM denoland/deno:bin-${DENO_VERSION} AS deno

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    STUDIO_ENABLE_CODE_NODES=1 STUDIO_CODE_RUNTIME=subprocess \
    STUDIO_CODE_NO_NETWORK=1 STUDIO_CODE_RUN_AS=61000 STUDIO_CODE_CONCURRENCY=4 \
    STUDIO_CODE_PACKAGES=pydantic,python-dateutil \
    STUDIO_CODE_TS_DENO_DIR=/opt/deno-cache STUDIO_CODE_TS_PACKAGES=npm:zod@3,npm:date-fns@4 \
    DENO_NO_UPDATE_CHECK=1 NO_COLOR=1 PORT=8080
COPY --from=deno /deno /usr/local/bin/deno
COPY docker/studio-code-ts/deps.ts /opt/studio-deps/deps.ts
RUN DENO_DIR=/opt/deno-cache deno cache --no-config --no-lock /opt/studio-deps/deps.ts \
    && chmod -R a+rX /opt/deno-cache && rm -rf /opt/studio-deps \
    && pip install httpx==0.28.1 pydantic==2.14.1 python-dateutil==2.9.0.post0
WORKDIR /srv
# Only the modules the Code runtime needs (no database, no API, no credentials code).
COPY backend/app/__init__.py backend/app/sandbox_service.py app/
COPY backend/app/core/__init__.py backend/app/core/config.py backend/app/core/errors.py backend/app/core/logging.py app/core/
COPY backend/app/engine/__init__.py backend/app/engine/code_runtime.py backend/app/engine/code_languages.py backend/app/engine/issues.py app/engine/
COPY backend/app/engine/sandbox/ app/engine/sandbox/
RUN chmod -R a+rX /srv && python -c "import app.sandbox_service"
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8080\")}/healthz',timeout=2).status==200 else 1)"
CMD ["python", "-m", "app.sandbox_service"]
