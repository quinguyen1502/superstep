#!/usr/bin/env bash
# Live integration test of both SDKs: starts the backend on a temporary database, signs in as the dev admin, creates a
# workflow token and isolated chat app keys, then runs both SDKs' workflow and chat tests.
#
#   scripts/sdk_integration.sh
#
# Needs: backend deps (BACKEND_PYTHON, default backend/.venv/bin/python), the Python SDK installed in SDK_PYTHON
# (default sdk/python/.venv/bin/python) and `npm ci` done in sdk/typescript. PORT defaults to 8130.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${PORT:-8130}"
BACKEND_PYTHON="${BACKEND_PYTHON:-$ROOT/backend/.venv/bin/python}"
SDK_PYTHON="${SDK_PYTHON:-$ROOT/sdk/python/.venv/bin/python}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/superstep-sdk-it.XXXXXX")"
BASE="http://127.0.0.1:$PORT"

cleanup() { [[ -n "${PID:-}" ]] && kill "$PID" 2>/dev/null || true; rm -rf "$WORK"; }
trap cleanup EXIT

(cd "$ROOT/backend" && DATABASE_URL= REDIS_URL= STUDIO_DB="$WORK/it.db" STUDIO_IMPORT_DIR="$WORK/imports" STUDIO_SECRET_KEY_FILE="$WORK/secret.key" \
  OPENAI_API_KEY= STUDIO_ENABLE_DEMO_TOOLS=1 STUDIO_TRIGGER_RATE_LIMIT=0 \
  STUDIO_PUBLIC_CHAT_RATE_READ=0 STUDIO_PUBLIC_CHAT_RATE_VISITOR=0 STUDIO_PUBLIC_CHAT_RATE_IP=0 STUDIO_PUBLIC_CHAT_RATE_USER=0 \
  "$BACKEND_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" >"$WORK/backend.log" 2>&1) &
PID=$!
for _ in $(seq 1 120); do curl -fsS "$BASE/api/health" >/dev/null 2>&1 && break; sleep 0.5; done
curl -fsS "$BASE/api/health" >/dev/null || { cat "$WORK/backend.log"; exit 1; }

# Owner side (JWT): sign in and create a workflow token. The token stays in this process's environment only.
read -r WID TOKEN < <("$SDK_PYTHON" "$ROOT/scripts/sdk_chat_seed.py" "$BASE" "$WORK/chat.json")
export SUPERSTEP_IT_BASE_URL="$BASE" SUPERSTEP_IT_WORKFLOW_ID="$WID" SUPERSTEP_IT_TOKEN="$TOKEN"
export SUPERSTEP_IT_CHAT_CONFIG="$WORK/chat.json"

echo "== Python SDK (live)"
(cd "$ROOT/sdk/python" && "$SDK_PYTHON" -m pytest -q tests/test_integration.py tests/test_chat_integration.py -rs)
echo "== TypeScript SDK (live)"
(cd "$ROOT/sdk/typescript" && npm run --silent test:integration)
