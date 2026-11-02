#!/usr/bin/env bash
# Isolated, cross-origin sample acceptance. No real credentials, models, package publication or screenshot commits.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PYTHON="${BACKEND_PYTHON:-$ROOT/backend/.venv/bin/python}"
API_PORT="${CHAT_HOST_API_PORT:-8131}"
HOST_PORT="${CHAT_HOST_PORT:-5188}"
SECOND_PORT="${CHAT_HOST_SECOND_PORT:-5189}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/superstep-chat-host.XXXXXX")"
BASE="http://127.0.0.1:$API_PORT"
HOST="http://localhost:$HOST_PORT"
cleanup() {
  for task_pid in "${API_PID:-}" "${HOST_PID:-}" "${SECOND_PID:-}"; do [[ -z "$task_pid" ]] || kill "$task_pid" 2>/dev/null || true; done
  rm -rf "$WORK"
}
trap cleanup EXIT
cd "$ROOT"
"$BACKEND_PYTHON" scripts/check_test_ports.py "$API_PORT" "$HOST_PORT" "$SECOND_PORT"
npm --prefix sdk/typescript run build
npm run build --workspace=@superstep/react
node node_modules/typescript/bin/tsc -p examples/chat-host/tsconfig.json
node node_modules/vite/bin/vite.js build --config frontend/vite.chat-host.config.ts
node frontend/scripts/check-ui-classes.mjs --strict examples/chat-host/src/app.tsx
node --test examples/chat-host/tests/server.test.mjs

(cd backend && DATABASE_URL= REDIS_URL= STUDIO_DB="$WORK/host.db" STUDIO_IMPORT_DIR="$WORK/imports" STUDIO_SECRET_KEY_FILE="$WORK/key" \
  OPENAI_API_KEY= STUDIO_ATTACHMENT_STORAGE=db STUDIO_ENABLE_DEMO_TOOLS=1 STUDIO_TRIGGER_RATE_LIMIT=0 STUDIO_PUBLIC_CHAT_RATE_READ=0 \
  STUDIO_PUBLIC_CHAT_RATE_VISITOR=0 STUDIO_PUBLIC_CHAT_RATE_IP=0 STUDIO_PUBLIC_CHAT_RATE_USER=0 \
  "$BACKEND_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" >"$WORK/backend.log" 2>&1) &
API_PID=$!
for _ in $(seq 1 120); do curl -fsS "$BASE/api/health" >/dev/null 2>&1 && break; sleep 0.5; done
curl -fsS "$BASE/api/health" >/dev/null || { cat "$WORK/backend.log"; exit 1; }
SUPERSTEP_IT_CHAT_ORIGIN="$HOST" SUPERSTEP_IT_CHAT_SPARE_KEY=1 "$BACKEND_PYTHON" scripts/sdk_chat_seed.py "$BASE" "$WORK/config.json" >"$WORK/seed.env"
export CHAT_HOST_DEMO=1 CHAT_HOST_FIXTURE="$WORK/config.json" CHAT_HOST_PORT="$HOST_PORT" CHAT_HOST_SECOND_PORT="$SECOND_PORT"
node examples/chat-host/tests/fixture-host.mjs >"$WORK/host.log" 2>&1 &
HOST_PID=$!
CHAT_HOST_PORT="$SECOND_PORT" node examples/chat-host/tests/fixture-host.mjs >"$WORK/second.log" 2>&1 &
SECOND_PID=$!
for _ in $(seq 1 80); do curl -fsS "$HOST/health" >/dev/null 2>&1 && break; sleep 0.25; done
curl -fsS "$HOST/health" >/dev/null || { cat "$WORK/host.log"; exit 1; }
for _ in $(seq 1 80); do curl -fsS "http://localhost:$SECOND_PORT/health" >/dev/null 2>&1 && break; sleep 0.25; done
curl -fsS "http://localhost:$SECOND_PORT/health" >/dev/null || { cat "$WORK/second.log"; exit 1; }
node node_modules/@playwright/test/cli.js test --config frontend/playwright.chat-host.config.ts "$@"
