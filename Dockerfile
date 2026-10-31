# All-in-one image for PaaS one-click deploys (Render, Heroku, Railway, Coolify, Dokploy; docs/deploy/README.md).
# One container serves the built UI, /api and /ws on $PORT. No Docker daemon or socket: Code nodes run with the
# subprocess runtime (STUDIO_CODE_RUNTIME=subprocess, labelled "Runs on host" in the UI), and Deno is included so
# TypeScript Code nodes work too. SQLite in /data by default (mount a volume there); set DATABASE_URL for Postgres.
# No secret is baked in: JWT_SECRET and STUDIO_SECRET_KEY come from the platform at run time.
# Build: docker build -t superstep .   Run: docker run -p 8000:8000 -v superstep:/data -e JWT_SECRET=... -e STUDIO_SECRET_KEY=... superstep
ARG DENO_VERSION=2.9.8

FROM node:22-alpine AS web
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM denoland/deno:bin-${DENO_VERSION} AS deno

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    STUDIO_ENV=production \
    STUDIO_DB=/data/studio.db STUDIO_SECRET_KEY_FILE=/data/secret.key STUDIO_IMPORT_DIR=/data/imports \
    STUDIO_STATIC_DIR=/app/static \
    STUDIO_TRUSTED_PROXIES=10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,100.64.0.0/10 \
    STUDIO_ENABLE_CODE_NODES=1 STUDIO_CODE_RUNTIME=subprocess \
    STUDIO_CODE_PACKAGES=pydantic,python-dateutil \
    STUDIO_CODE_TS_DENO_DIR=/opt/deno-cache STUDIO_CODE_TS_PACKAGES=npm:zod@3,npm:date-fns@4 \
    DENO_NO_UPDATE_CHECK=1 NO_COLOR=1 \
    PORT=8000
COPY --from=deno /deno /usr/local/bin/deno
# The TypeScript allowlist, cached like docker/studio-code-ts (keep STUDIO_CODE_TS_PACKAGES equal to deps.ts)
COPY docker/studio-code-ts/deps.ts /opt/studio-deps/deps.ts
RUN DENO_DIR=/opt/deno-cache deno cache --no-config --no-lock /opt/studio-deps/deps.ts \
    && chmod -R a+rX /opt/deno-cache && rm -rf /opt/studio-deps
WORKDIR /app
COPY backend/pyproject.toml backend/alembic.ini ./
COPY backend/app ./app
RUN pip install ".[s3]" python-dateutil==2.9.0.post0 \
    && useradd -m -u 10001 studio && mkdir -p /data && chown studio /data
COPY --from=web /src/dist ./static
COPY docker/entrypoint.sh /usr/local/bin/superstep-entrypoint
# Starts as root only to chown a root-owned platform volume at /data, then drops to `studio` (docker/entrypoint.sh)
ENTRYPOINT ["superstep-entrypoint"]
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health',timeout=2).status==200 else 1)"
# Migrations + bootstrap run on start-up; one process per container (scale with a worker + Redis, see docs/deploy).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --proxy-headers --forwarded-allow-ips '*'"]
