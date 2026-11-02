# Web UI: production Vite build served by nginx; /api and /ws are proxied to the API. Build context: repository root (docker build -f frontend/Dockerfile .)
FROM node:22-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
COPY frontend/package.json ./frontend/package.json
COPY packages/react/package.json ./packages/react/package.json
COPY sdk/typescript/package.json ./sdk/typescript/package.json
RUN npm ci --workspace=frontend --workspace=@superstep/react --include-workspace-root=false
COPY frontend/ ./frontend/
COPY packages/react/ ./packages/react/
RUN npm run build --workspace=frontend

FROM nginx:1.27-alpine
ENV API_UPSTREAM=api:8000 WEB_MAX_BODY_SIZE=110m
COPY frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /src/frontend/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -qO- http://127.0.0.1/healthz >/dev/null || exit 1
