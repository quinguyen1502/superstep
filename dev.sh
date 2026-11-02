#!/usr/bin/env bash
# Khởi động backend (FastAPI :8000) + frontend (Vite :5173)
set -e
cd "$(dirname "$0")"
# Cài lại khi venv thiếu hoặc chưa có package (một venv rỗng làm uvicorn/pytest không chạy được)
if [ ! -x backend/.venv/bin/uvicorn ]; then
  [ -x backend/.venv/bin/python ] || python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q --prefer-binary -e "backend[dev]"
fi
[ -d node_modules ] || npm install
(cd backend && exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app) &
BE=$!
(cd frontend && exec npx vite --host 0.0.0.0 --port 5173) &
FE=$!
trap 'kill $BE $FE 2>/dev/null' INT TERM EXIT
echo "Backend: http://localhost:8000/docs  |  UI: http://localhost:5173"
wait
